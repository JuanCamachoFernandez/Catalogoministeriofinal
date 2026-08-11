"""eliminar galeria de ferias

Revision ID: 7f3c2a91d4b6
Revises: 4ad81f2c6b30
Create Date: 2026-08-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "7f3c2a91d4b6"
down_revision = "4ad81f2c6b30"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("imagenes_feria")


def downgrade():
    op.create_table(
        "imagenes_feria",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feria_id", sa.Uuid(), nullable=False),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column("direccion_url", sa.String(length=500), nullable=False),
        sa.Column("identificador_cloudinary", sa.String(length=500), nullable=True),
        sa.Column("texto_alternativo", sa.String(length=255), nullable=True),
        sa.Column("es_portada", sa.Boolean(), nullable=True),
        sa.Column("orden_visualizacion", sa.Integer(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["feria_id"],
            ["ferias.id"],
            name=op.f("foranea_imagenes_feria_feria_id_ferias"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("primaria_imagenes_feria")),
    )
