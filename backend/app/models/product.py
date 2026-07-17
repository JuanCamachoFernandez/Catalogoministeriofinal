from sqlalchemy import UniqueConstraint, select

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

    @classmethod
    def admin_query(cls, exhibitor_id=None, term=None):
        query = select(cls).where(cls.deleted_at.is_(None))
        if exhibitor_id:
            query = query.where(cls.exhibitor_id == exhibitor_id)
        if term:
            query = query.where(cls.nombre.ilike(f"%{term}%"))
        return query

    @classmethod
    def owned_query(cls, exhibitor_id):
        return select(cls).where(
            cls.exhibitor_id == exhibitor_id, cls.deleted_at.is_(None)
        )

    @classmethod
    def public_query(cls, exhibitor_id, term=None, category_id=None, status=None):
        query = select(cls).where(
            cls.exhibitor_id == exhibitor_id,
            cls.estado.in_([ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK]),
            cls.deleted_at.is_(None),
        )
        if term:
            query = query.where(cls.nombre.ilike(f"%{term}%"))
        if category_id:
            query = query.where(cls.category_id == category_id)
        if status:
            query = query.where(cls.estado == status)
        return query

    @classmethod
    def available_by_ids_query(cls, product_ids):
        return select(cls).where(
            cls.id.in_(product_ids),
            cls.estado == ProductStatus.AVAILABLE,
            cls.deleted_at.is_(None),
        )


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
