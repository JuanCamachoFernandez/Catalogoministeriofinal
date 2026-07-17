"""MVC, ciclo de ferias y tokens revocados."""

from alembic import op
import sqlalchemy as sa


revision = "c31d8a0e45f2"
down_revision = "8b8f9b7a9d31"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("fairs", "imagen_portada", existing_type=sa.String(length=500), nullable=True)
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"], unique=True)


def downgrade():
    op.drop_index("ix_revoked_tokens_jti", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.alter_column("fairs", "imagen_portada", existing_type=sa.String(length=500), nullable=False)
