"""ampliar nombres de producto a 255 caracteres

Revision ID: e9a6c13d4f25
Revises: d8f5b02c3e14
"""

from alembic import op
import sqlalchemy as sa


revision = "e9a6c13d4f25"
down_revision = "d8f5b02c3e14"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "productos", "nombre",
        existing_type=sa.String(length=200), type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        "productos", "nombre_comercial",
        existing_type=sa.String(length=200), type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "productos", "nombre_comercial",
        existing_type=sa.String(length=255), type_=sa.String(length=200),
        existing_nullable=True,
    )
    op.alter_column(
        "productos", "nombre",
        existing_type=sa.String(length=255), type_=sa.String(length=200),
        existing_nullable=False,
    )
