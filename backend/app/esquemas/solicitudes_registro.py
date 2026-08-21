from marshmallow import Schema, fields, validate


representative_name_validator = validate.And(
    validate.Length(min=1, max=100),
    validate.Regexp(
        r"^[^\W\d_]+(?:[ '’-][^\W\d_]+)*$",
        error="Use únicamente letras, espacios, apóstrofes o guiones.",
    ),
)

def optional_representative_name_validator(value):
    if value == "":
        return
    representative_name_validator(value)

bolivian_mobile_validator = validate.Regexp(
    r"^[67][0-9]{7}$",
    error="Ingrese 8 dígitos de un celular boliviano que comience con 6 o 7.",
)

email_validator = validate.And(
    validate.Length(max=255),
    validate.Regexp(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        error="Ingrese un correo electrónico válido.",
    ),
)

facebook_url_validator = validate.Regexp(
    r"(?i)^https://(?:(?:www|m|web)\.)?(?:facebook\.com|fb\.com)/\S+$",
    error="Ingrese una URL válida de Facebook que comience con https://.",
)

instagram_url_validator = validate.Regexp(
    r"(?i)^https://(?:www\.)?instagram\.com/\S+$",
    error="Ingrese una URL válida de Instagram que comience con https://.",
)

tiktok_url_validator = validate.Regexp(
    r"(?i)^https://(?:www\.)?tiktok\.com/@[^/?#\s]+.*$",
    error="Ingrese una URL válida de TikTok que comience con https://.",
)

commercial_name_validator = validate.And(
    validate.Length(min=1, max=200),
    validate.Regexp(
        r"^(?=.*\S)[^\x00-\x1f\x7f]+$",
        error="Use letras, numeros, espacios o signos visibles, sin saltos de linea.",
    ),
)


def _validar_registro_base(value: str, *, permitir_e_final: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    trimmed = value.strip()
    if not trimmed:
        return False
    if permitir_e_final and trimmed[-1:].upper() == "E":
        trimmed = trimmed[:-1]
    if not trimmed:
        return False
    if any(character not in "0123456789-_/" for character in trimmed):
        return False
    solo_digitos = trimmed.replace("-", "").replace("_", "").replace("/", "")
    return solo_digitos.isdigit() and 5 <= len(solo_digitos) <= 12


def registro_nit_validator(value: str) -> None:
    if not _validar_registro_base(value):
        raise validate.ValidationError(
            "El NIT debe contener entre 5 y 12 dígitos; también puede incluir guiones (-), guion bajo (_) o barras (/)."
        )


def registro_seprec_validator(value: str) -> None:
    if not _validar_registro_base(value):
        raise validate.ValidationError(
            "El registro SEPREC debe contener entre 5 y 12 dígitos; también puede incluir guiones (-), guion bajo (_) o barras (/)."
        )


def registro_pro_bolivia_validator(value: str) -> None:
    if not _validar_registro_base(value, permitir_e_final=True):
        raise validate.ValidationError(
            "El registro PRO-BOLIVIA debe contener entre 5 y 12 dígitos; puede incluir guiones (-), guion bajo (_) o barras (/), y una E final opcional."
        )


class RequestedSectorSchema(Schema):
    productive_sector_id = fields.UUID(required=True)
    detalle_otro = fields.String(allow_none=True, validate=validate.Length(max=255))


class RequestedProductSchema(Schema):
    nombre_comercial = fields.String(required=True, validate=validate.Length(min=1, max=200))
    descripcion_tecnica = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    precio_referencia = fields.Decimal(required=True, places=2, as_string=True, validate=validate.Range(min=0))
    imagen_url = fields.String(required=True, validate=validate.Length(min=1, max=500))


class RegistrationRequestSchema(Schema):
    nombre_comercial = fields.String(required=True, validate=commercial_name_validator)
    razon_social = fields.String(required=True, validate=validate.Length(min=1, max=200))
    nit = fields.String(
        allow_none=True,
        validate=registro_nit_validator,
    )
    registro_seprec = fields.String(
        allow_none=True,
        validate=registro_seprec_validator,
    )
    registro_pro_bolivia = fields.String(
        allow_none=True,
        validate=registro_pro_bolivia_validator,
    )
    nombres_representante = fields.String(
        required=True, validate=representative_name_validator
    )
    apellido_paterno_representante = fields.String(
        required=True, validate=representative_name_validator
    )
    apellido_materno_representante = fields.String(
        required=True, validate=optional_representative_name_validator
    )
    departamento = fields.String(required=True, validate=validate.Length(min=1, max=80))
    direccion_fisica = fields.String(required=True, validate=validate.Length(min=1, max=255))
    telefono_whatsapp = fields.String(required=True, validate=bolivian_mobile_validator)
    correo_electronico = fields.Email(required=True, validate=email_validator)
    facebook_url = fields.Url(allow_none=True, schemes={"https"}, validate=facebook_url_validator)
    instagram_url = fields.Url(allow_none=True, schemes={"https"}, validate=instagram_url_validator)
    tiktok_url = fields.Url(allow_none=True, schemes={"https"}, validate=tiktok_url_validator)
    resena_comercial = fields.String(required=True, validate=validate.Length(min=1, max=5000))
    logo_url = fields.String(required=True, validate=validate.Length(min=1, max=500))
    sectores = fields.List(fields.Nested(RequestedSectorSchema), required=True, validate=validate.Length(min=1))
    productos = fields.List(
        fields.Nested(RequestedProductSchema),
        required=True,
        validate=validate.Length(equal=3),
    )


class RejectRegistrationRequestSchema(Schema):
    motivo = fields.String(required=True, validate=validate.Length(min=1, max=2000))
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))


class ApproveRegistrationRequestSchema(Schema):
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))
