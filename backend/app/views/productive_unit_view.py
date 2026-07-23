from marshmallow import Schema, fields, validate

from .registration_request_view import RequestedSectorSchema, representative_name_validator


class ProductiveUnitUpdateSchema(Schema):
    nombre_comercial = fields.String(validate=validate.Length(min=1, max=200))
    razon_social = fields.String(validate=validate.Length(min=1, max=200))
    nit = fields.String(
        allow_none=True,
        validate=validate.Regexp(
            r"^[0-9]{5,12}$",
            error="El NIT debe contener entre 5 y 12 dígitos, sin guiones ni otros caracteres.",
        ),
    )
    registro_seprec = fields.String(
        allow_none=True,
        validate=validate.Regexp(
            r"^[0-9]{5,12}$",
            error="El registro SEPREC debe contener entre 5 y 12 dígitos, sin guiones ni otros caracteres.",
        ),
    )
    registro_pro_bolivia = fields.String(
        allow_none=True,
        validate=validate.Regexp(
            r"^[0-9]{5,12}$",
            error="El registro PRO-BOLIVIA debe contener entre 5 y 12 dígitos, sin guiones ni otros caracteres.",
        ),
    )
    nombres_representante = fields.String(validate=representative_name_validator)
    apellido_paterno_representante = fields.String(validate=representative_name_validator)
    apellido_materno_representante = fields.String(validate=representative_name_validator)
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
