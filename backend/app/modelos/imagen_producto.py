from sqlalchemy import Index, UniqueConstraint

from ..extensiones import db
from .base import now, uid


class ProductImage(db.Model):
    __tablename__ = "imagenes_producto"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    product_id = db.Column(
        "producto_id",
        db.Uuid,
        db.ForeignKey("productos.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = db.Column("nombre_archivo", db.String(255), nullable=False)
    url = db.Column("direccion_url", db.String(500), nullable=False)
    alt_text = db.Column("texto_alternativo", db.String(255))
    is_cover = db.Column("es_portada", db.Boolean, default=False, nullable=False)
    display_order = db.Column("orden_visualizacion", db.Integer, default=0, nullable=False)
    created_at = db.Column(
        "fecha_creacion", db.DateTime(timezone=True), default=now, nullable=False
    )
    updated_at = db.Column(
        "fecha_actualizacion", db.DateTime(timezone=True), default=now, onupdate=now, nullable=False
    )
    __table_args__ = (
        Index("indice_imagenes_producto_producto_id", "producto_id"),
        UniqueConstraint(
            "producto_id",
            "orden_visualizacion",
            name="imagen_producto_orden_unico",
        ),
        Index(
            "imagen_producto_portada_unica",
            "producto_id",
            unique=True,
            postgresql_where=db.text("es_portada IS TRUE"),
            sqlite_where=db.text("es_portada IS 1"),
        ),
    )

__all__ = ["ProductImage"]
