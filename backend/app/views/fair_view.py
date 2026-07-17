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
    imagen_portada = fields.String(required=True, validate=validate.Length(min=1, max=500))
    observaciones = fields.String(load_default=None, allow_none=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["fecha_fin"] < data["fecha_inicio"]:
            raise ValidationError(
                {"fecha_fin": ["La fecha final no puede ser anterior a la inicial"]}
            )


class FairUpdateSchema(Schema):
    nombre = fields.String(validate=validate.Length(min=1, max=200))
    descripcion = fields.String(allow_none=True)
    lugar = fields.String(validate=validate.Length(min=1, max=200))
    direccion = fields.String(allow_none=True, validate=validate.Length(max=255))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    municipio = fields.String(validate=validate.Length(min=1, max=100))
    fecha_inicio = fields.Date()
    fecha_fin = fields.Date()
    imagen_portada = fields.String(validate=validate.Length(min=1, max=500))
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
