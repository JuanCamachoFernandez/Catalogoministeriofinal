"""Ajusta expositor y precio de producto"""
from alembic import op
import sqlalchemy as sa

revision = "8b8f9b7a9d31"
down_revision = "62cb1fe0782c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("precio", sa.Numeric(10, 2), nullable=True))
    op.drop_column("exhibitors", "razon_social")
    op.alter_column("exhibitors", "email_gmail", new_column_name="correo")
    op.alter_column("exhibitors", "fotografia_perfil", new_column_name="logo")


def downgrade():
    op.alter_column("exhibitors", "logo", new_column_name="fotografia_perfil")
    op.alter_column("exhibitors", "correo", new_column_name="email_gmail")
    op.add_column("exhibitors", sa.Column("razon_social", sa.String(length=200), nullable=True))
    op.drop_column("products", "precio")
