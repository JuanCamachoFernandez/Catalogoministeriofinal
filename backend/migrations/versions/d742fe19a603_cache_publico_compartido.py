"""Agrega version compartida para la cache publica."""

from alembic import op
import sqlalchemy as sa


revision = "d742fe19a603"
down_revision = "c31d8a0e45f2"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "cache_states",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.bulk_insert(table, [{"key": "public_catalog", "version": 0}])


def downgrade():
    op.drop_table("cache_states")
