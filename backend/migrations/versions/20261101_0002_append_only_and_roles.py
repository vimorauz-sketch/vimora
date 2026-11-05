"""append-only triggers, roles and permissions

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APPEND_ONLY = ["audit_logs", "payment_events", "order_events"]


def upgrade() -> None:
    # Append-only enforcement at the database level: rows can be inserted but never updated
    # or deleted, even by application bugs. (A DB superuser can still bypass; restrict DB roles.)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vimora_forbid_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Table % is append-only', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for t in APPEND_ONLY:
        op.execute(f"CREATE TRIGGER {t}_append_only BEFORE UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION vimora_forbid_mutation();")
    # Financial records: confirmed payment amounts can never change once SUCCEEDED.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vimora_protect_payment() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Payments cannot be deleted' USING ERRCODE = 'insufficient_privilege';
            END IF;
            IF OLD.status = 'SUCCEEDED' AND (NEW.amount_minor <> OLD.amount_minor OR NEW.currency <> OLD.currency
                 OR NEW.order_id <> OLD.order_id OR NEW.provider_transaction_id IS DISTINCT FROM OLD.provider_transaction_id) THEN
                RAISE EXCEPTION 'Confirmed payment fields are immutable' USING ERRCODE = 'insufficient_privilege';
            END IF;
            IF OLD.status = 'SUCCEEDED' AND NEW.status NOT IN ('SUCCEEDED', 'REFUNDED') THEN
                RAISE EXCEPTION 'Invalid payment status change from SUCCEEDED' USING ERRCODE = 'insufficient_privilege';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("CREATE TRIGGER payments_protect BEFORE UPDATE OR DELETE ON payments FOR EACH ROW EXECUTE FUNCTION vimora_protect_payment();")
    op.execute("CREATE TRIGGER invoices_no_delete BEFORE DELETE ON invoices FOR EACH ROW EXECUTE FUNCTION vimora_forbid_mutation();")

    from app.security.permissions import PERMISSIONS, ROLE_PERMISSIONS

    roles = sa.table("roles", sa.column("id", sa.BigInteger), sa.column("name", sa.String), sa.column("description", sa.String))
    perms = sa.table("permissions", sa.column("id", sa.BigInteger), sa.column("code", sa.String), sa.column("description", sa.String))
    rp = sa.table("role_permissions", sa.column("role_id", sa.BigInteger), sa.column("permission_id", sa.BigInteger))
    role_desc = {"SUPER_ADMIN": "Platform owner", "ADMIN": "Administrator", "SUPPORT": "Support staff", "CUSTOMER": "Customer"}
    op.bulk_insert(roles, [{"id": i + 1, "name": n, "description": role_desc[n]} for i, n in enumerate(role_desc)])
    codes = list(PERMISSIONS)
    op.bulk_insert(perms, [{"id": i + 1, "code": c, "description": PERMISSIONS[c]} for i, c in enumerate(codes)])
    rows = []
    for i, n in enumerate(role_desc):
        for c in sorted(ROLE_PERMISSIONS.get(n, set())):
            rows.append({"role_id": i + 1, "permission_id": codes.index(c) + 1})
    op.bulk_insert(rp, rows)
    op.execute("SELECT setval(pg_get_serial_sequence('roles','id'), (SELECT MAX(id) FROM roles))")
    op.execute("SELECT setval(pg_get_serial_sequence('permissions','id'), (SELECT MAX(id) FROM permissions))")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS invoices_no_delete ON invoices")
    op.execute("DROP TRIGGER IF EXISTS payments_protect ON payments")
    for t in APPEND_ONLY:
        op.execute(f"DROP TRIGGER IF EXISTS {t}_append_only ON {t}")
    op.execute("DROP FUNCTION IF EXISTS vimora_protect_payment()")
    op.execute("DROP FUNCTION IF EXISTS vimora_forbid_mutation()")
    op.execute("DELETE FROM role_permissions; DELETE FROM permissions; DELETE FROM roles;")
