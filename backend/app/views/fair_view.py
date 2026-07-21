from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from ..models import AssignmentStatus, FeriaStatus


class FairCreateSchema(Schema):
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=200))
    descripcion = fields.String(load_default=None, allow_none=True)
    lugar = fields.String(required=True, validate=validate.Length(min=1, max=200))
    direccion = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255))
    departamento = fields.String(required=True, validate=validate.Length(min=1, max=80))
    municipio = fields.String(required=True, validate=validate.Length(min=1, max=100))
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)
    imagen_portada = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=1, max=500))
    observaciones = fields.String(load_default=None, allow_none=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise ValidationError(
                {"fecha_fin": ["La fecha final no puede ser anterior a la inicial"]}
            )


class FairUpdateSchema(Schema):
    id = fields.Raw(load_only=True)
    slug = fields.Raw(load_only=True)
    estado = fields.Raw(load_only=True)
    visible_publicamente = fields.Raw(load_only=True)
    hora_inicio = fields.Raw(load_only=True, allow_none=True)
    hora_fin = fields.Raw(load_only=True, allow_none=True)
    fecha_limite_registro = fields.Raw(load_only=True, allow_none=True)
    nombre = fields.String(validate=validate.Length(min=1, max=200))
    descripcion = fields.String(allow_none=True)
    lugar = fields.String(validate=validate.Length(min=1, max=200))
    direccion = fields.String(allow_none=True, validate=validate.Length(max=255))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    municipio = fields.String(validate=validate.Length(min=1, max=100))
    fecha_inicio = fields.Date()
    fecha_fin = fields.Date()
    imagen_portada = fields.String(allow_none=True, validate=validate.Length(min=1, max=500))
    observaciones = fields.String(allow_none=True)


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
    nombre = fields.String(required=True, validate=validate.Length(min=1, max=200))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=5000))
    ubicacion = fields.String(required=True, validate=validate.Length(min=1, max=255))
    departamento = fields.String(load_default="Bolivia", validate=validate.Length(min=1, max=80))
    municipio = fields.String(load_default="No especificado", validate=validate.Length(min=1, max=100))
    fecha_inicio = fields.Date(required=True)
    fecha_fin = fields.Date(required=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise ValidationError({"fecha_fin": ["La fecha final no puede ser anterior a la inicial"]})


class CanonicalFairUpdateSchema(Schema):
    nombre = fields.String(validate=validate.Length(min=1, max=200))
    descripcion = fields.String(allow_none=True, validate=validate.Length(max=5000))
    ubicacion = fields.String(validate=validate.Length(min=1, max=255))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    municipio = fields.String(validate=validate.Length(min=1, max=100))
    fecha_inicio = fields.Date()
    fecha_fin = fields.Date()


class ParticipationCreateSchema(Schema):
    productive_unit_id = fields.UUID(required=True)
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))


class ParticipationUpdateSchema(Schema):
    observaciones = fields.String(allow_none=True, validate=validate.Length(max=2000))
