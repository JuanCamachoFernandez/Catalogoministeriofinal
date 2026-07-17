from sqlalchemy import UniqueConstraint

from ..extensions import db
from .base import TimestampMixin, now, uid
from .enums import ProductStatus


class Category(TimestampMixin, db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True))


class Product(TimestampMixin, db.Model):
    __tablename__ = "products"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    exhibitor_id = db.Column(
        db.Uuid, db.ForeignKey("exhibitors.id"), nullable=False, index=True
    )
    category_id = db.Column(
        db.Uuid, db.ForeignKey("categories.id"), nullable=False, index=True
    )
    nombre = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    materiales_o_ingredientes = db.Column(db.Text)
    lugar_origen = db.Column(db.String(150))
    presentacion = db.Column(db.String(150))
    informacion_adicional = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2))
    estado = db.Column(
        db.Enum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.AVAILABLE,
    )
    destacado = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("exhibitor_id", "slug"),)


class ProductImage(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    product_id = db.Column(
        db.Uuid, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255))
    is_cover = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
