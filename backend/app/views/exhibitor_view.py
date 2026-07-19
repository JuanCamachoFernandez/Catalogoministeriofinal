from marshmallow import Schema, fields, validate

from ..models import DocumentType, UserStatus


class ExhibitorCreateSchema(Schema):
    nombre_comercial = fields.String(required=True, validate=validate.Length(min=1, max=200))
    tipo_documento = fields.Enum(DocumentType, by_value=True, load_default=DocumentType.CI)
    numero_documento = fields.String(required=True, validate=validate.Length(min=1, max=50))
    nombre_responsable = fields.String(required=True, validate=validate.Length(min=1, max=100))
    apellido_responsable = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    apellido_paterno_responsable = fields.String(validate=validate.Length(min=1, max=100))
    apellido_materno_responsable = fields.String(validate=validate.Length(min=1, max=100))
    correo = fields.Email(required=True, validate=validate.Length(max=255))
    telefono_whatsapp = fields.String(required=True, validate=validate.Length(min=8, max=20))
    departamento = fields.String(required=True, validate=validate.Length(min=1, max=80))
    municipio = fields.String(required=True, validate=validate.Length(min=1, max=100))
    direccion = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255))
    descripcion = fields.String(load_default=None, allow_none=True)
    descripcion_productos = fields.String(load_default=None, allow_none=True)
    nombre_tipo_expositor = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=200))
    logo = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))
    type_ids = fields.List(fields.UUID(), required=True, validate=validate.Length(equal=1))


class ExhibitorUpdateSchema(Schema):
    id = fields.Raw(load_only=True)
    user_id = fields.Raw(load_only=True)
    estado = fields.Raw(load_only=True)
    created_at = fields.Raw(load_only=True)
    tipos_expositor = fields.Raw(load_only=True)
    type_ids = fields.List(fields.UUID(), validate=validate.Length(equal=1))
    nombre_comercial = fields.String(validate=validate.Length(min=1, max=200))
    tipo_documento = fields.Enum(DocumentType, by_value=True)
    numero_documento = fields.String(validate=validate.Length(min=1, max=50))
    nombre_responsable = fields.String(validate=validate.Length(min=1, max=100))
    apellido_responsable = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    apellido_paterno_responsable = fields.String(validate=validate.Length(min=1, max=100))
    apellido_materno_responsable = fields.String(validate=validate.Length(min=1, max=100))
    correo = fields.Email(validate=validate.Length(max=255))
    telefono_whatsapp = fields.String(validate=validate.Length(min=8, max=20))
    departamento = fields.String(validate=validate.Length(min=1, max=80))
    municipio = fields.String(validate=validate.Length(min=1, max=100))
    direccion = fields.String(allow_none=True, validate=validate.Length(max=255))
    descripcion = fields.String(allow_none=True)
    descripcion_productos = fields.String(allow_none=True)
    nombre_tipo_expositor = fields.String(allow_none=True, validate=validate.Length(max=200))
    logo = fields.String(allow_none=True, validate=validate.Length(max=500))


class ExhibitorStatusSchema(Schema):
    status = fields.Enum(UserStatus, by_value=True, required=True)
