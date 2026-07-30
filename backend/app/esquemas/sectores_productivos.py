from marshmallow import Schema, fields, validate


class ProductiveSectorSchema(Schema):
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=150))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=2000))
    es_otro = fields.Boolean(load_default=False)


class ProductiveSectorUpdateSchema(Schema):
    nombre = fields.String(validate=validate.Length(min=1, max=150))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=2000))
    es_otro = fields.Boolean()


class ProductiveSectorStatusSchema(Schema):
    estado = fields.String(required=True, validate=validate.OneOf(["ACTIVE", "INACTIVE"]))
