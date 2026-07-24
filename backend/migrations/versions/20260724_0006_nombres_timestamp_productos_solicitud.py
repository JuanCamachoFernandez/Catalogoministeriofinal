"""Alinea los nombres de timestamp de los productos de registro."""

from alembic import op


revision = "20260724_0006"
down_revision = "20260723_0005"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "productos_solicitud_registro",
        "created_at",
        new_column_name="fecha_creacion",
    )
    op.alter_column(
        "productos_solicitud_registro",
        "updated_at",
        new_column_name="fecha_actualizacion",
    )


def downgrade():
    op.alter_column(
        "productos_solicitud_registro",
        "fecha_actualizacion",
        new_column_name="updated_at",
    )
    op.alter_column(
        "productos_solicitud_registro",
        "fecha_creacion",
        new_column_name="created_at",
    )
