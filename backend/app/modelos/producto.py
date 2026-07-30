from sqlalchemy import Index, UniqueConstraint, select

from ..extensiones import db
from .base import TimestampMixin, uid
from .enumeraciones import ProductStatus


class Category(TimestampMixin, db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column("identificador_url", db.String(140), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column("fecha_eliminacion", db.DateTime(timezone=True))


class Product(TimestampMixin, db.Model):
    __tablename__ = "productos"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    exhibitor_id = db.Column(
        "expositor_id", db.Uuid, db.ForeignKey("expositores.id"), nullable=True, index=True
    )
    productive_unit_id = db.Column(
        "unidad_productiva_id",
        db.Uuid,
        db.ForeignKey("unidades_productivas.id"),
        nullable=True,
        index=True,
    )
    category_id = db.Column(
        "categoria_id", db.Uuid, db.ForeignKey("categorias.id"), nullable=True, index=True
    )
    nombre = db.Column(db.String(200), nullable=False)
    slug = db.Column("identificador_url", db.String(220), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    materiales_o_ingredientes = db.Column(db.Text)
    lugar_origen = db.Column(db.String(150))
    presentacion = db.Column(db.String(150))
    informacion_adicional = db.Column(db.Text)
    nombre_comercial = db.Column(db.String(200))
    descripcion_tecnica = db.Column(db.Text)
    materia_prima = db.Column(db.Text)
    dimensiones = db.Column(db.String(255))
    colores_disponibles = db.Column(db.String(255))
    certificaciones = db.Column(db.Text)
    presentacion_empaque = db.Column(db.String(255))
    precio_referencia = db.Column(db.Numeric(10, 2))
    capacidad_produccion_stock = db.Column(db.String(255))
    precio = db.Column(db.Numeric(10, 2))
    estado = db.Column(
        db.Enum(ProductStatus, name="estado_producto"),
        nullable=False,
        default=ProductStatus.AVAILABLE,
    )
    destacado = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column("fecha_eliminacion", db.DateTime(timezone=True))
    __table_args__ = (
        Index("indice_productos_estado", "estado"),
        UniqueConstraint(
            "expositor_id",
            "identificador_url",
            name="producto_expositor_url_unico",
        ),
    )

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

    @classmethod
    def publicable_query(cls, productive_unit_id=None):
        from .imagen_producto import ProductImage

        image_counts = (
            select(ProductImage.product_id, db.func.count(ProductImage.id).label("image_count"))
            .group_by(ProductImage.product_id)
            .subquery()
        )
        query = (
            select(cls)
            .join(image_counts, image_counts.c.product_id == cls.id)
            .where(
                cls.productive_unit_id.is_not(None),
                cls.estado.in_([ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK]),
                cls.deleted_at.is_(None),
                image_counts.c.image_count == 3,
            )
        )
        if productive_unit_id:
            query = query.where(cls.productive_unit_id == productive_unit_id)
        return query
