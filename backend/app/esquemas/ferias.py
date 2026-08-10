from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from ..modelos import AssignmentStatus, FeriaStatus

FAIR_TYPES = ("FAIR", "EVENT")
EVENT_ANIMATIONS = ("AURORA", "SHIMMER", "FLOAT", "GLOW")
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
HEX_COLOR = validate.Regexp(
    r"^#[0-9A-Fa-f]{6}$",
    error="Use un color hexadecimal v\u00e1lido, por ejemplo #1A2B3C.",
)


def _validate_event_theme(data, partial=False):
    fair_type = data.get("tipo", "FAIR")
    if fair_type not in FAIR_TYPES:
        raise ValidationError({"tipo": ["Tipo inv\u00e1lido"]})
    if fair_type != "EVENT":
        return
    required_fields = ("color_primario", "color_secundario", "color_terciario")
    missing = [field for field in required_fields if not data.get(field)]
    if missing and not partial:
        raise ValidationError(
            {field: ["Este color es obligatorio para un evento."] for field in missing}
        )
    animations = data.get("animaciones_tema") or []
    if not animations:
        raise ValidationError(
            {"animaciones_tema": ["Seleccione al menos una animaci\u00f3n para el evento."]}
        )


class FairCreateSchema(Schema):
    tipo = fields.String(
        load_default="FAIR",
        validate=validate.OneOf(FAIR_TYPES),
    )
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=200))
    descripcion = fields.String(load_default=None, allow_none=True)
    lugar = fields.String(required=True, validate=validate.Length(min=1, max=200))
    direccion = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255))
    departamento = fields.String(required=True, validate=validate.Length(min=1, max=80))
    departamentos = fields.List(
        fields.String(validate=validate.OneOf(BOLIVIA_DEPARTMENTS)),
        load_default=list,
        validate=validate.Length(max=len(BOLIVIA_DEPARTMENTS)),
    )
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    imagen_portada = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=1, max=500))
    color_primario = fields.String(load_default=None, allow_none=True, validate=HEX_COLOR)
    color_secundario = fields.String(load_default=None, allow_none=True, validate=HEX_COLOR)
    color_terciario = fields.String(load_default=None, allow_none=True, validate=HEX_COLOR)
    animaciones_tema = fields.List(
        fields.String(validate=validate.OneOf(EVENT_ANIMATIONS)),
        load_default=list,
    )
    observaciones = fields.String(load_default=None, allow_none=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise ValidationError(
                {"fecha_fin": ["La fecha final no puede ser anterior a la inicial"]}
            )
        _validate_event_theme(data)


class FairUpdateSchema(Schema):
    id = fields.Raw(load_only=True)
    slug = fields.Raw(load_only=True)
    estado = fields.Raw(load_only=True)
    visible_publicamente = fields.Raw(load_only=True)
    hora_inicio = fields.Raw(load_only=True, allow_none=True)
    hora_fin = fields.Raw(load_only=True, allow_none=True)
    fecha_limite_registro = fields.Raw(load_only=True, allow_none=True)
    tipo = fields.String(validate=validate.OneOf(FAIR_TYPES))
    nombre = fields.String(validate=validate.Length(min=1, max=200))
    descripcion = fields.String(allow_none=True)
    lugar = fields.String(validate=validate.Length(min=1, max=200))
    direccion = fields.String(allow_none=True, validate=validate.Length(max=255))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    departamentos = fields.List(
        fields.String(validate=validate.OneOf(BOLIVIA_DEPARTMENTS)),
        validate=validate.Length(max=len(BOLIVIA_DEPARTMENTS)),
    )
    fecha_inicio = fields.Date()
    fecha_fin = fields.Date()
    imagen_portada = fields.String(allow_none=True, validate=validate.Length(min=1, max=500))
    color_primario = fields.String(allow_none=True, validate=HEX_COLOR)
    color_secundario = fields.String(allow_none=True, validate=HEX_COLOR)
    color_terciario = fields.String(allow_none=True, validate=HEX_COLOR)
    animaciones_tema = fields.List(
        fields.String(validate=validate.OneOf(EVENT_ANIMATIONS))
    )
    observaciones = fields.String(allow_none=True)

    @validates_schema
    def validate_event_theme(self, data, **kwargs):
        if any(
            field in data
            for field in (
                "tipo",
                "color_primario",
                "color_secundario",
                "color_terciario",
                "animaciones_tema",
            )
        ):
            _validate_event_theme(data, partial=True)


class FairStatusSchema(Schema):
    status = fields.Enum(
        FeriaStatus,
        by_value=True,
        required=True,
        validate=validate.OneOf([FeriaStatus.FINISHED, FeriaStatus.DISABLED]),
    )


class AssignmentCreateSchema(Schema):
    exhibitor_id = fields.UUID(required=True)
    estado = fields.Enum(
        AssignmentStatus, by_value=True, load_default=AssignmentStatus.AUTHORIZED
    )
    numero_stand = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=40))
    sector = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    observaciones = fields.String(load_default=None, allow_none=True)


class AssignmentUpdateSchema(Schema):
    estado = fields.Enum(AssignmentStatus, by_value=True)
    numero_stand = fields.String(allow_none=True, validate=validate.Length(max=40))
    sector = fields.String(allow_none=True, validate=validate.Length(max=100))
    observaciones = fields.String(allow_none=True)


class CanonicalFairCreateSchema(Schema):
    tipo = fields.String(
        load_default="FAIR",
        validate=validate.OneOf(FAIR_TYPES),
    )
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=200))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=5000))
    ubicacion = fields.String(required=True, validate=validate.Length(min=1, max=255))
    departamento = fields.String(load_default="Bolivia", validate=validate.Length(min=1, max=80))
    departamentos = fields.List(
        fields.String(validate=validate.OneOf(BOLIVIA_DEPARTMENTS)),
        load_default=list,
        validate=validate.Length(max=len(BOLIVIA_DEPARTMENTS)),
    )
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    color_primario = fields.String(load_default=None, allow_none=True, validate=HEX_COLOR)
    color_secundario = fields.String(load_default=None, allow_none=True, validate=HEX_COLOR)
    color_terciario = fields.String(load_default=None, allow_none=True, validate=HEX_COLOR)
    animaciones_tema = fields.List(
        fields.String(validate=validate.OneOf(EVENT_ANIMATIONS)),
        load_default=list,
    )

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise ValidationError({"fecha_fin": ["La fecha final no puede ser anterior a la inicial"]})
        _validate_event_theme(data)
        if data.get("tipo") == "EVENT" and not data.get("departamentos"):
            raise ValidationError({"departamentos": ["Seleccione al menos un departamento."]})


class CanonicalFairUpdateSchema(Schema):
    tipo = fields.String(validate=validate.OneOf(FAIR_TYPES))
    nombre = fields.String(validate=validate.Length(min=1, max=200))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=5000))
    ubicacion = fields.String(validate=validate.Length(min=1, max=255))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    departamentos = fields.List(
        fields.String(validate=validate.OneOf(BOLIVIA_DEPARTMENTS)),
        validate=validate.Length(max=len(BOLIVIA_DEPARTMENTS)),
    )
    fecha_inicio = fields.Date()
    fecha_fin = fields.Date()
    color_primario = fields.String(allow_none=True, validate=HEX_COLOR)
    color_secundario = fields.String(allow_none=True, validate=HEX_COLOR)
    color_terciario = fields.String(allow_none=True, validate=HEX_COLOR)
    animaciones_tema = fields.List(
        fields.String(validate=validate.OneOf(EVENT_ANIMATIONS))
    )

    @validates_schema
    def validate_event_theme(self, data, **kwargs):
        if data.get("tipo") == "EVENT" and not data.get("departamentos"):
            raise ValidationError({"departamentos": ["Seleccione al menos un departamento."]})
        if any(
            field in data
            for field in (
                "tipo",
                "color_primario",
                "color_secundario",
                "color_terciario",
                "animaciones_tema",
            )
        ):
            _validate_event_theme(data, partial=True)


class ParticipationCreateSchema(Schema):
    productive_unit_id = fields.UUID(required=True)
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))


class ParticipationUpdateSchema(Schema):
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))
