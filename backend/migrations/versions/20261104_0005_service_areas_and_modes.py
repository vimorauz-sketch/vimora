"""service areas, service modes (ONLINE/REMOTE/LOCAL/FUTURE/DISABLED), local order handover

Additive only: no existing column is changed or dropped and no existing row is rewritten,
so orders, payments and audit history are untouched. Legacy services keep service_mode = NULL
(treated as ONLINE) until `seed-catalog` classifies them.

Revision ID: 0005
Revises: 0004
"""
import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _t(uz: str, en: str, ru: str) -> str:
    return json.dumps({"uz": uz, "en": en, "ru": ru}, ensure_ascii=False)


AREAS = [
    # slug, kind, name, region, district, locality, local_enabled, sort
    ("qarapchi", "LOCALITY", _t("Qarapchi qishlog'i", "Qarapchi village", "Кишлак Карапчи"), "Jizzax viloyati", "Zomin tumani", "Qarapchi", True, 10),
    ("zomin-city", "LOCALITY", _t("Zomin shahri", "Zomin town", "Город Зомин"), "Jizzax viloyati", "Zomin tumani", "Zomin", False, 20),
    ("zomin-district", "DISTRICT", _t("Zomin tumani (boshqa joy)", "Zomin district (elsewhere)", "Зоминский район (другое место)"), "Jizzax viloyati", "Zomin tumani", "", False, 30),
    ("jizzakh-region", "REGION", _t("Jizzax viloyati (boshqa joy)", "Jizzakh region (elsewhere)", "Джизакская область (другое место)"), "Jizzax viloyati", "", "", False, 40),
    ("other", "OTHER", _t("Boshqa hudud (O'zbekiston)", "Other region (Uzbekistan)", "Другой регион (Узбекистан)"), "", "", "", False, 90),
]


def upgrade() -> None:
    op.create_table(
        "service_areas",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("name", JSONB(), nullable=False),
        sa.Column("region", sa.String(120), nullable=False, server_default=""),
        sa.Column("district", sa.String(120), nullable=False, server_default=""),
        sa.Column("locality", sa.String(120), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("local_services_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rules", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("pickup_address", sa.Text(), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    areas = sa.table("service_areas", sa.column("slug"), sa.column("kind"), sa.column("name", JSONB), sa.column("region"), sa.column("district"),
                     sa.column("locality"), sa.column("is_active"), sa.column("local_services_enabled"), sa.column("sort_order"))
    op.bulk_insert(areas, [
        {"slug": s, "kind": k, "name": json.loads(n), "region": r, "district": d, "locality": loc, "is_active": True, "local_services_enabled": le, "sort_order": so}
        for s, k, n, r, d, loc, le, so in AREAS
    ])

    op.add_column("services", sa.Column("service_mode", sa.String(20), nullable=True))
    op.add_column("services", sa.Column("service_area_id", sa.BigInteger(), sa.ForeignKey("service_areas.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("services", sa.Column("requires_file", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_services_service_mode", "services", ["service_mode"])

    op.add_column("orders", sa.Column("service_area_id", sa.BigInteger(), sa.ForeignKey("service_areas.id", ondelete="RESTRICT"), nullable=True))
    op.add_column("orders", sa.Column("is_local", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("orders", sa.Column("handover_method", sa.String(10), nullable=True))
    op.add_column("orders", sa.Column("handover_status", sa.String(30), nullable=True))
    op.add_column("orders", sa.Column("handover", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.create_index("ix_orders_service_area_id", "orders", ["service_area_id"])
    op.create_index("ix_orders_local_handover", "orders", ["is_local", "handover_method", "handover_status"])
    op.create_check_constraint("handover_method_valid", "orders", "handover_method IS NULL OR handover_method IN ('PICKUP','MEETUP')")
    op.create_check_constraint("local_has_handover", "orders", "NOT is_local OR handover_method IS NOT NULL")
    op.create_check_constraint("mode_valid", "services", "service_mode IS NULL OR service_mode IN ('ONLINE','REMOTE','LOCAL','FUTURE','DISABLED')")


def downgrade() -> None:
    op.drop_constraint("ck_services_mode_valid", "services")
    op.drop_constraint("ck_orders_local_has_handover", "orders")
    op.drop_constraint("ck_orders_handover_method_valid", "orders")
    op.drop_index("ix_orders_local_handover", "orders")
    op.drop_index("ix_orders_service_area_id", "orders")
    for c in ("handover", "handover_status", "handover_method", "is_local", "service_area_id"):
        op.drop_column("orders", c)
    op.drop_index("ix_services_service_mode", "services")
    for c in ("requires_file", "service_area_id", "service_mode"):
        op.drop_column("services", c)
    op.drop_table("service_areas")
