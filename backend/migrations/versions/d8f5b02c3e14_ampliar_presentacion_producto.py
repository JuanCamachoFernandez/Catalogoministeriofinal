"""ampliar presentacion de producto a 255 caracteres

Revision ID: d8f5b02c3e14
Revises: c7e4a91b2d03
"""

from alembic import op
import sqlalchemy as sa


revision = "d8f5b02c3e14"
down_revision = "c7e4a91b2d03"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "productos", "presentacion",
        existing_type=sa.String(length=150), type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "productos", "presentacion",
        existing_type=sa.String(length=255), type_=sa.String(length=150),
        existing_nullable=True,
    )
