from marshmallow import Schema, fields, validate


class RequestedSectorSchema(Schema):
    productive_sector_id = fields.UUID(required=True)
    detalle_otro = fields.String(allow_none=True, validate=validate.Length(max=255))


class RegistrationRequestSchema(Schema):
    nombre_comercial = fields.String(required=True, validate=validate.Length(min=1, max=200))
    razon_social = fields.String(required=True, validate=validate.Length(min=1, max=200))
    nit = fields.String(allow_none=True, validate=validate.Length(max=50))
    registro_seprec = fields.String(allow_none=True, validate=validate.Length(max=100))
    registro_pro_bolivia = fields.String(allow_none=True, validate=validate.Length(max=100))
    nombre_representante = fields.String(required=True, validate=validate.Length(min=1, max=200))
    departamento = fields.String(required=True, validate=validate.Length(min=1, max=80))
    direccion_fisica = fields.String(required=True, validate=validate.Length(min=1, max=255))
    telefono_whatsapp = fields.String(required=True, validate=validate.Regexp(r"^\+?[0-9 ()-]{7,30}$"))
    correo_electronico = fields.Email(required=True, validate=validate.Length(max=255))
    facebook_url = fields.Url(allow_none=True, schemes={"http", "https"})
    instagram_url = fields.Url(allow_none=True, schemes={"http", "https"})
    tiktok_url = fields.Url(allow_none=True, schemes={"http", "https"})
    resena_comercial = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    logo_url = fields.String(allow_none=True, validate=validate.Length(max=500))
    sectores = fields.List(fields.Nested(RequestedSectorSchema), required=True, validate=validate.Length(min=1))


class RejectRegistrationRequestSchema(Schema):
    motivo = fields.String(required=True, validate=validate.Length(min=1, max=2000))
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))


class ApproveRegistrationRequestSchema(Schema):
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))
