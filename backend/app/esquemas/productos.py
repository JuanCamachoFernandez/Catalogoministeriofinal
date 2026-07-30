from marshmallow import Schema, fields, pre_load, validate, validates_schema, ValidationError

from ..modelos import ProductStatus


def _letters_numbers_spaces(value):
    text = value.strip()
    if not text or any(not (character.isalnum() or character.isspace()) for character in text):
        raise ValidationError("Use solamente letras, números y espacios")


def _letters_spaces(value):
    text = value.strip()
    if not text or any(not (character.isalpha() or character.isspace()) for character in text):
        raise ValidationError("Use solamente letras y espacios")


def _integer_text(value):
    if not value.strip().isdigit():
        raise ValidationError("Ingrese únicamente un número entero")


class ProductCreateSchema(Schema):
    exhibitor_id = fields.UUID(load_default=None, allow_none=True)
    category_id = fields.UUID(required=True)
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=200))
    descripcion = fields.String(required=True, validate=validate.Length(min=1))
    precio = fields.Decimal(load_default=None, allow_none=True, places=2, as_string=True)
    estado = fields.Enum(ProductStatus, by_value=True, load_default=ProductStatus.AVAILABLE)
    materiales_o_ingredientes = fields.String(load_default=None, allow_none=True)
    lugar_origen = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    presentacion = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    informacion_adicional = fields.String(load_default=None, allow_none=True)
    destacado = fields.Boolean(load_default=False)

    @pre_load
    def normalize_empty_values(self, data, **kwargs):
        data = dict(data)
        if data.get("exhibitor_id") == "":
            data["exhibitor_id"] = None
        if data.get("precio") == "":
            data["precio"] = None
        return data


class ProductUpdateSchema(Schema):
    category_id = fields.UUID()
    nombre = fields.String(validate=validate.Length(min=1, max=200))
    descripcion = fields.String(validate=validate.Length(min=1))
    precio = fields.Decimal(allow_none=True, places=2, as_string=True)
    estado = fields.Enum(ProductStatus, by_value=True)
    materiales_o_ingredientes = fields.String(allow_none=True)
    lugar_origen = fields.String(allow_none=True, validate=validate.Length(max=150))
    presentacion = fields.String(allow_none=True, validate=validate.Length(max=150))
    informacion_adicional = fields.String(allow_none=True)
    destacado = fields.Boolean()


class ProductImageUpdateSchema(Schema):
    is_cover = fields.Boolean()
    alt_text = fields.String(allow_none=True, validate=validate.Length(max=255))
    display_order = fields.Integer(validate=validate.Range(min=0))


class WhatsAppItemSchema(Schema):
    product_id = fields.UUID(required=True)
    quantity = fields.Integer(required=True, validate=validate.Range(min=1, max=999))


class WhatsAppSchema(Schema):
    fair_slug = fields.String(required=True, validate=validate.Length(min=1, max=220))
    items = fields.List(fields.Nested(WhatsAppItemSchema), validate=validate.Length(min=1, max=50))
    product_ids = fields.List(fields.UUID(), validate=validate.Length(min=1, max=50))

    @validates_schema
    def require_products(self, data, **kwargs):
        if not data.get("items") and not data.get("product_ids"):
            raise ValidationError("Seleccione al menos un producto")


class ProductiveProductCreateSchema(Schema):
    nombre_comercial = fields.String(required=True, validate=validate.And(validate.Length(min=1, max=200), _letters_numbers_spaces))
    descripcion_tecnica = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    materia_prima = fields.String(required=True, validate=validate.And(validate.Length(min=1, max=2000), _letters_numbers_spaces))
    dimensiones = fields.String(allow_none=True, validate=validate.Length(max=255))
    colores_disponibles = fields.String(allow_none=True, validate=validate.And(validate.Length(max=255), _letters_spaces))
    certificaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))
    presentacion_empaque = fields.String(required=True, validate=validate.And(validate.Length(min=1, max=255), _letters_numbers_spaces))
    precio_referencia = fields.Decimal(required=True, places=2, as_string=True, validate=validate.Range(min=0))
    capacidad_produccion_stock = fields.String(required=True, validate=validate.And(validate.Length(min=1, max=255), _integer_text))


class ProductiveProductUpdateSchema(Schema):
    nombre_comercial = fields.String(validate=validate.And(validate.Length(min=1, max=200), _letters_numbers_spaces))
    descripcion_tecnica = fields.String(validate=validate.Length(min=1, max=5000))
    materia_prima = fields.String(validate=validate.And(validate.Length(min=1, max=2000), _letters_numbers_spaces))
    dimensiones = fields.String(allow_none=True, validate=validate.Length(max=255))
    colores_disponibles = fields.String(allow_none=True, validate=validate.And(validate.Length(max=255), _letters_spaces))
    certificaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))
    presentacion_empaque = fields.String(validate=validate.And(validate.Length(min=1, max=255), _letters_numbers_spaces))
    precio_referencia = fields.Decimal(places=2, as_string=True, validate=validate.Range(min=0))
    capacidad_produccion_stock = fields.String(validate=validate.And(validate.Length(min=1, max=255), _integer_text))


class ProductiveProductStatusSchema(Schema):
    estado = fields.String(required=True, validate=validate.OneOf(["DRAFT", "AVAILABLE", "OUT_OF_STOCK", "RETIRED"]))


class ProductImageOrderSchema(Schema):
    image_ids = fields.List(fields.UUID(), required=True, validate=validate.Length(min=1, max=3))


def productive_product_json(product):
    from sqlalchemy import select

    from ..extensiones import db
    from ..modelos import ProductImage

    images = db.session.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.display_order, ProductImage.created_at)
    ).all()
    return {
        "id": str(product.id),
        "productive_unit_id": str(product.productive_unit_id),
        "nombre_comercial": product.nombre_comercial,
        "descripcion_tecnica": product.descripcion_tecnica,
        "materia_prima": product.materia_prima,
        "dimensiones": product.dimensiones,
        "colores_disponibles": product.colores_disponibles,
        "certificaciones": product.certificaciones,
        "presentacion_empaque": product.presentacion_empaque,
        "precio_referencia": float(product.precio_referencia) if product.precio_referencia is not None else None,
        "capacidad_produccion_stock": product.capacidad_produccion_stock,
        "estado": product.estado.value,
        "fecha_registro": product.created_at.isoformat(),
        "fecha_actualizacion": product.updated_at.isoformat(),
        "imagenes": [
            {
                "id": str(image.id),
                "url_imagen": image.url,
                "texto_alternativo": image.alt_text,
                "orden_visualizacion": image.display_order,
                "es_principal": bool(image.is_cover),
                "fecha_registro": image.created_at.isoformat(),
                "fecha_actualizacion": image.updated_at.isoformat(),
            }
            for image in images
        ],
        "publicable": product.estado in (ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK) and len(images) == 3 and product.deleted_at is None,
    }
