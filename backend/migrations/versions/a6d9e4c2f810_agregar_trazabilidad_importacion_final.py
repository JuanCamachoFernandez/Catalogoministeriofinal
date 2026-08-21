"""agregar trazabilidad importacion final

Revision ID: a6d9e4c2f810
Revises: 7f3c2a91d4b6
"""

from alembic import op
import sqlalchemy as sa


revision = "a6d9e4c2f810"
down_revision = "7f3c2a91d4b6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ejecuciones_importacion_final",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_hash", sa.String(64), nullable=False),
        sa.Column("general_sheet_id", sa.String(255), nullable=False),
        sa.Column("corrected_sheet_id", sa.String(255), nullable=False),
        sa.Column("general_sheet_hash", sa.String(64), nullable=False),
        sa.Column("corrected_sheet_hash", sa.String(64), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("resumen", sa.JSON(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_finalizacion", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_hash"),
    )
    op.create_table(
        "filas_fuente_importacion_final",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ejecucion_id", sa.Uuid(), nullable=False),
        sa.Column("fuente", sa.String(20), nullable=False),
        sa.Column("sheet_id", sa.String(255), nullable=False),
        sa.Column("hoja", sa.String(255), nullable=False),
        sa.Column("numero_fila", sa.Integer(), nullable=False),
        sa.Column("hash_fila", sa.String(64), nullable=False),
        sa.Column("unidad_productiva_id", sa.Uuid(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ejecucion_id"], ["ejecuciones_importacion_final.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unidad_productiva_id"], ["unidades_productivas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fuente", "sheet_id", "hoja", "numero_fila", name="fila_fuente_importacion_unica"),
    )
    op.create_table(
        "entidades_importacion_final",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fila_fuente_id", sa.Uuid(), nullable=False),
        sa.Column("tipo_entidad", sa.String(40), nullable=False),
        sa.Column("entidad_id", sa.Uuid(), nullable=False),
        sa.Column("clave_entidad", sa.String(255), nullable=False),
        sa.Column("drive_file_id", sa.String(255), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fila_fuente_id"], ["filas_fuente_importacion_final.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fila_fuente_id", "tipo_entidad", "clave_entidad", name="entidad_importada_unica"),
    )


def downgrade():
    op.drop_table("entidades_importacion_final")
    op.drop_table("filas_fuente_importacion_final")
    op.drop_table("ejecuciones_importacion_final")
