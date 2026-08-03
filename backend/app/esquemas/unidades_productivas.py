from marshmallow import Schema, fields, validate

from .solicitudes_registro import (
    RequestedSectorSchema,
    bolivian_mobile_validator,
    email_validator,
    facebook_url_validator,
    instagram_url_validator,
    representative_name_validator,
    tiktok_url_validator,
)


BOLIVIA_DEPARTMENTS = (
    "Chuquisaca",
    "La Paz",
    "Cochabamba",
    "Oruro",
    "Potosí",
    "Tarija",
    "Santa Cruz",
    "Beni",
    "Pando",
)

alphanumeric_profile_validator = validate.And(
    validate.Length(min=1, max=200),
    validate.Regexp(
        r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$",
        error="Use solamente letras, números y espacios.",
    ),
)

profile_person_name_validator = validate.And(
    validate.Length(min=1, max=100),
    validate.Regexp(
        r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$",
        error="Use solamente letras y espacios.",
    ),
)


class AdminProductiveUnitCreateSchema(Schema):
    nombre_comercial = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
    )
    razon_social = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
    )
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
    nombres_representante = fields.String(
        required=True,
        validate=representative_name_validator,
    )
    apellido_paterno_representante = fields.String(
        required=True,
        validate=representative_name_validator,
    )
    apellido_materno_representante = fields.String(
        required=True,
        validate=representative_name_validator,
    )
    departamento = fields.String(
        required=True,
        validate=validate.OneOf(
            BOLIVIA_DEPARTMENTS,
            error="Seleccione uno de los nueve departamentos de Bolivia.",
        ),
    )
    direccion_fisica = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255),
    )
    telefono_whatsapp = fields.String(
        required=True,
        validate=bolivian_mobile_validator,
    )
    correo_electronico = fields.Email(
        required=True,
        validate=email_validator,
    )
    facebook_url = fields.Url(
        allow_none=True,
        schemes={"https"},
        validate=facebook_url_validator,
    )
    instagram_url = fields.Url(
        allow_none=True,
        schemes={"https"},
        validate=instagram_url_validator,
    )
    tiktok_url = fields.Url(
        allow_none=True,
        schemes={"https"},
        validate=tiktok_url_validator,
    )
    resena_comercial = fields.String(
        required=True,
        validate=validate.Length(min=1, max=5000),
    )
    logo_url = fields.String(
        allow_none=True,
        validate=validate.Length(min=1, max=500),
    )
    sectores = fields.List(
        fields.Nested(RequestedSectorSchema),
        required=True,
        validate=validate.Length(min=1),
    )


class ProductiveUnitUpdateSchema(Schema):
    nombre_comercial = fields.String(validate=alphanumeric_profile_validator)
    razon_social = fields.String(validate=alphanumeric_profile_validator)
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
    nombres_representante = fields.String(validate=profile_person_name_validator)
    apellido_paterno_representante = fields.String(
        validate=profile_person_name_validator
    )
    apellido_materno_representante = fields.String(
        validate=profile_person_name_validator
    )
    departamento = fields.String(
        validate=validate.OneOf(
            BOLIVIA_DEPARTMENTS,
            error="Seleccione uno de los nueve departamentos de Bolivia.",
        )
    )
    direccion_fisica = fields.String(validate=validate.Length(min=1, max=255))
    telefono_whatsapp = fields.String(validate=bolivian_mobile_validator)
    correo_electronico = fields.Email(validate=email_validator)
    facebook_url = fields.Url(
        allow_none=True,
        schemes={"https"},
        validate=facebook_url_validator,
    )
    instagram_url = fields.Url(
        allow_none=True,
        schemes={"https"},
        validate=instagram_url_validator,
    )
    tiktok_url = fields.Url(
        allow_none=True,
        schemes={"https"},
        validate=tiktok_url_validator,
    )
    resena_comercial = fields.String(validate=validate.Length(min=1, max=5000))


class ProductiveUnitStatusSchema(Schema):
    estado = fields.String(
        required=True,
        validate=validate.OneOf(["ACTIVE", "INACTIVE"]),
    )


class UnitSectorsSchema(Schema):
    sectores = fields.List(
        fields.Nested(RequestedSectorSchema),
        required=True,
        validate=validate.Length(min=1),
    )
