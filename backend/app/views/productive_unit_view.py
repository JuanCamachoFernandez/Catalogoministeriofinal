from marshmallow import Schema, fields, validate

from .registration_request_view import RequestedSectorSchema


class ProductiveUnitUpdateSchema(Schema):
    nombre_comercial = fields.String(validate=validate.Length(min=1, max=200))
    razon_social = fields.String(validate=validate.Length(min=1, max=200))
    nit = fields.String(allow_none=True, validate=validate.Length(max=50))
    registro_seprec = fields.String(allow_none=True, validate=validate.Length(max=100))
    registro_pro_bolivia = fields.String(allow_none=True, validate=validate.Length(max=100))
    nombre_representante = fields.String(validate=validate.Length(min=1, max=200))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    direccion_fisica = fields.String(validate=validate.Length(min=1, max=255))
    telefono_whatsapp = fields.String(validate=validate.Regexp(r"^\+?[0-9 ()-]{7,30}$"))
    correo_electronico = fields.Email(validate=validate.Length(max=255))
    facebook_url = fields.Url(allow_none=True, schemes={"http", "https"})
    instagram_url = fields.Url(allow_none=True, schemes={"http", "https"})
    tiktok_url = fields.Url(allow_none=True, schemes={"http", "https"})
    resena_comercial = fields.String(validate=validate.Length(min=1, max=5000))


class ProductiveUnitStatusSchema(Schema):
    estado = fields.String(required=True, validate=validate.OneOf(["ACTIVE", "INACTIVE", "SUSPENDED"]))


class UnitSectorsSchema(Schema):
    sectores = fields.List(fields.Nested(RequestedSectorSchema), required=True, validate=validate.Length(min=1))
