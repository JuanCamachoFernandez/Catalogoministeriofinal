"""Índices de consulta e integridad de imágenes de producto."""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0003"
down_revision = "20260721_0002"
branch_labels = None
depends_on = None


def upgrade():
    # Normaliza primero los datos heredados para que las restricciones sean
    # aplicables sin perder imágenes.
    op.execute(
        """
        WITH ordenadas AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY producto_id
                       ORDER BY orden_visualizacion NULLS LAST, fecha_creacion, id
                   ) - 1 AS nuevo_orden
              FROM imagenes_producto
        )
        UPDATE imagenes_producto AS imagen
           SET orden_visualizacion = ordenadas.nuevo_orden
          FROM ordenadas
         WHERE imagen.id = ordenadas.id
        """
    )
    op.execute(
        """
        WITH portadas AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY producto_id
                       ORDER BY es_portada DESC NULLS LAST,
                                orden_visualizacion, fecha_creacion, id
                   ) AS posicion
              FROM imagenes_producto
        )
        UPDATE imagenes_producto AS imagen
           SET es_portada = (portadas.posicion = 1)
          FROM portadas
         WHERE imagen.id = portadas.id
        """
    )

    op.alter_column(
        "imagenes_producto",
        "es_portada",
        existing_type=sa.Boolean(),
        nullable=False,
    )
    op.alter_column(
        "imagenes_producto",
        "orden_visualizacion",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_index("indice_ferias_estado", "ferias", ["estado"])
    op.create_index("indice_ferias_fecha_inicio", "ferias", ["fecha_inicio"])
    op.create_index("indice_ferias_fecha_fin", "ferias", ["fecha_fin"])
    op.create_index("indice_productos_estado", "productos", ["estado"])
    op.create_index(
        "indice_imagenes_producto_producto_id",
        "imagenes_producto",
        ["producto_id"],
    )
    op.create_unique_constraint(
        "imagen_producto_orden_unico",
        "imagenes_producto",
        ["producto_id", "orden_visualizacion"],
    )
    op.create_index(
        "imagen_producto_portada_unica",
        "imagenes_producto",
        ["producto_id"],
        unique=True,
        postgresql_where=sa.text("es_portada IS TRUE"),
    )


def downgrade():
    op.drop_index("imagen_producto_portada_unica", table_name="imagenes_producto")
    op.drop_constraint(
        "imagen_producto_orden_unico", "imagenes_producto", type_="unique"
    )
    op.drop_index(
        "indice_imagenes_producto_producto_id", table_name="imagenes_producto"
    )
    op.drop_index("indice_productos_estado", table_name="productos")
    op.drop_index("indice_ferias_fecha_fin", table_name="ferias")
    op.drop_index("indice_ferias_fecha_inicio", table_name="ferias")
    op.drop_index("indice_ferias_estado", table_name="ferias")
    op.alter_column(
        "imagenes_producto",
        "orden_visualizacion",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "imagenes_producto",
        "es_portada",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )
