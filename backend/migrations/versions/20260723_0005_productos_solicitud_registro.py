"""Agrega productos obligatorios a la solicitud de registro."""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0005"
down_revision = "20260722_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "productos_solicitud_registro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("registration_request_id", sa.Uuid(), nullable=False),
        sa.Column("nombre_comercial", sa.String(length=200), nullable=False),
        sa.Column("descripcion_tecnica", sa.Text(), nullable=False),
        sa.Column("precio_referencia", sa.Numeric(10, 2), nullable=False),
        sa.Column("imagen_url", sa.String(length=500), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["registration_request_id"],
            ["solicitudes_registro.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "registration_request_id",
            "orden",
            name="producto_solicitud_registro_orden_unico",
        ),
    )
    op.create_index(
        "ix_productos_solicitud_registro_registration_request_id",
        "productos_solicitud_registro",
        ["registration_request_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_productos_solicitud_registro_registration_request_id",
        table_name="productos_solicitud_registro",
    )
    op.drop_table("productos_solicitud_registro")
