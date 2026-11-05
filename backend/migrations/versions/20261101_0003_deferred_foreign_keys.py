"""deferred (circular) foreign keys

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-01
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

FKS = [
    ("fk_attachments_message_id_messages", "attachments", "messages", "message_id"),
    ("fk_orders_accepted_quotation_id_quotations", "orders", "quotations", "accepted_quotation_id"),
    ("fk_services_image_attachment_id_attachments", "services", "attachments", "image_attachment_id"),
]


def upgrade() -> None:
    for name, src, ref, col in FKS:
        op.create_foreign_key(name, src, ref, [col], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    for name, src, _, _ in FKS:
        op.drop_constraint(name, src, type_="foreignkey")
