from marshmallow import Schema, fields, pre_load, validate, validates_schema, ValidationError

from ..models import ProductStatus


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
