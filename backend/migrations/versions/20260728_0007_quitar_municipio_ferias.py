"""Quita municipio de las ferias."""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0007"
down_revision = "20260724_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("ferias", "municipio")


def downgrade():
    op.add_column(
        "ferias",
        sa.Column("municipio", sa.String(length=100), nullable=False, server_default=""),
    )
    op.alter_column("ferias", "municipio", server_default=None)
