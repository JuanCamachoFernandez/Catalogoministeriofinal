from marshmallow import Schema, fields, validate


class CategoryCreateSchema(Schema):
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=120))
    descripcion = fields.String(load_default=None, allow_none=True)


class CategoryUpdateSchema(Schema):
    nombre = fields.String(validate=validate.Length(min=1, max=120))
    descripcion = fields.String(allow_none=True)


class CategoryStatusSchema(Schema):
    active = fields.Boolean(required=True)
