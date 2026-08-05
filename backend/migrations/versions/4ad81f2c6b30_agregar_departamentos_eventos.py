"""Agregar departamentos múltiples para eventos

Revision ID: 4ad81f2c6b30
Revises: 9f2c7b1a4d10
Create Date: 2026-08-05 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "4ad81f2c6b30"
down_revision = "9f2c7b1a4d10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ferias", sa.Column("departamentos", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("ferias", "departamentos")
