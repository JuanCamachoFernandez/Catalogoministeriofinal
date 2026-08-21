"""preservar datos ambiguos de importacion

Revision ID: c7e4a91b2d03
Revises: a6d9e4c2f810
"""

from alembic import op
import sqlalchemy as sa


revision = "c7e4a91b2d03"
down_revision = "a6d9e4c2f810"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "filas_fuente_importacion_final",
        sa.Column("datos_originales", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "filas_fuente_importacion_final",
        sa.Column("advertencias", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "filas_fuente_importacion_final",
        sa.Column("es_ambiguo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "filas_fuente_importacion_final",
        sa.Column("motivos_pendientes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "filas_fuente_importacion_final",
        sa.Column("es_pendiente", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_constraint("fila_fuente_importacion_unica", "filas_fuente_importacion_final", type_="unique")
    op.create_unique_constraint(
        "fila_fuente_importacion_unica", "filas_fuente_importacion_final",
        ["ejecucion_id", "fuente", "sheet_id", "hoja", "numero_fila"],
    )


def downgrade():
    op.drop_constraint("fila_fuente_importacion_unica", "filas_fuente_importacion_final", type_="unique")
    op.create_unique_constraint(
        "fila_fuente_importacion_unica", "filas_fuente_importacion_final",
        ["fuente", "sheet_id", "hoja", "numero_fila"],
    )
    op.drop_column("filas_fuente_importacion_final", "es_pendiente")
    op.drop_column("filas_fuente_importacion_final", "motivos_pendientes")
    op.drop_column("filas_fuente_importacion_final", "es_ambiguo")
    op.drop_column("filas_fuente_importacion_final", "advertencias")
    op.drop_column("filas_fuente_importacion_final", "datos_originales")
