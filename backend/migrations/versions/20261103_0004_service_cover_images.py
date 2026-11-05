"""service cover images

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("services", sa.Column("cover_image_url", sa.String(length=500), nullable=True))
    op.add_column("services", sa.Column("cover_image_credit", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("services", "cover_image_credit")
    op.drop_column("services", "cover_image_url")
