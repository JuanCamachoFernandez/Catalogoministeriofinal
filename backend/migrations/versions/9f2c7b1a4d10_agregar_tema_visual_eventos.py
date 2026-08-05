"""Agregar tema visual para eventos

Revision ID: 9f2c7b1a4d10
Revises: b1c3a5d7e9f0
Create Date: 2026-08-05 15:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f2c7b1a4d10"
down_revision = "b1c3a5d7e9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ferias",
        sa.Column("tipo", sa.String(length=20), nullable=False, server_default="FAIR"),
    )
    op.add_column("ferias", sa.Column("color_primario", sa.String(length=7), nullable=True))
    op.add_column("ferias", sa.Column("color_secundario", sa.String(length=7), nullable=True))
    op.add_column("ferias", sa.Column("color_terciario", sa.String(length=7), nullable=True))
    op.add_column("ferias", sa.Column("animaciones_tema", sa.JSON(), nullable=True))
    op.alter_column("ferias", "tipo", server_default=None)


def downgrade():
    op.drop_column("ferias", "animaciones_tema")
    op.drop_column("ferias", "color_terciario")
    op.drop_column("ferias", "color_secundario")
    op.drop_column("ferias", "color_primario")
    op.drop_column("ferias", "tipo")
