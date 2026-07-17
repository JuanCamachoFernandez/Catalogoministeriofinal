from marshmallow import Schema, fields, validate

from ..models import DocumentType, UserStatus


class ExhibitorCreateSchema(Schema):
    nombre_comercial = fields.String(required=True, validate=validate.Length(min=1, max=200))
    tipo_documento = fields.Enum(DocumentType, by_value=True, load_default=DocumentType.CI)
    numero_documento = fields.String(required=True, validate=validate.Length(min=1, max=50))
    nombre_responsable = fields.String(required=True, validate=validate.Length(min=1, max=100))
    apellido_responsable = fields.String(required=True, validate=validate.Length(min=1, max=100))
    correo = fields.Email(required=True, validate=validate.Length(max=255))
    telefono_whatsapp = fields.String(required=True, validate=validate.Length(min=8, max=20))
    departamento = fields.String(required=True, validate=validate.Length(min=1, max=80))
    municipio = fields.String(required=True, validate=validate.Length(min=1, max=100))
    direccion = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255))
    descripcion = fields.String(load_default=None, allow_none=True)
    descripcion_productos = fields.String(load_default=None, allow_none=True)
    logo = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))
    type_ids = fields.List(fields.UUID(), required=True, validate=validate.Length(min=1))


class ExhibitorUpdateSchema(Schema):
    nombre_comercial = fields.String(validate=validate.Length(min=1, max=200))
    tipo_documento = fields.Enum(DocumentType, by_value=True)
    numero_documento = fields.String(validate=validate.Length(min=1, max=50))
    nombre_responsable = fields.String(validate=validate.Length(min=1, max=100))
    apellido_responsable = fields.String(validate=validate.Length(min=1, max=100))
    correo = fields.Email(validate=validate.Length(max=255))
    telefono_whatsapp = fields.String(validate=validate.Length(min=8, max=20))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    municipio = fields.String(validate=validate.Length(min=1, max=100))
    direccion = fields.String(allow_none=True, validate=validate.Length(max=255))
    descripcion = fields.String(allow_none=True)
    descripcion_productos = fields.String(allow_none=True)
    logo = fields.String(allow_none=True, validate=validate.Length(max=500))


class ExhibitorStatusSchema(Schema):
    status = fields.Enum(UserStatus, by_value=True, required=True)
