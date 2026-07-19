from marshmallow import Schema, fields, validate

from ..models import Role, UserStatus


class AdminCreateSchema(Schema):
    first_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    # last_name se acepta únicamente para clientes anteriores a los apellidos separados.
    last_name = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    paternal_last_name = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    maternal_last_name = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    apellido_paterno = fields.String(validate=validate.Length(min=1, max=100))
    apellido_materno = fields.String(validate=validate.Length(min=1, max=100))
    numero_documento = fields.String(required=True, validate=validate.Length(min=1, max=50))
    email = fields.Email(required=True, validate=validate.Length(max=255))
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=15))
    cargo = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    unidad = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=150))
    observaciones = fields.String(load_default=None, allow_none=True)
    role = fields.Enum(
        Role,
        by_value=True,
        load_default=Role.ADMIN_VICEMINISTERIO,
        validate=validate.OneOf([Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO]),
    )


class AdminUpdateSchema(Schema):
    first_name = fields.String(validate=validate.Length(min=1, max=100))
    last_name = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    paternal_last_name = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    maternal_last_name = fields.String(load_only=True, validate=validate.Length(min=1, max=100))
    apellido_paterno = fields.String(validate=validate.Length(min=1, max=100))
    apellido_materno = fields.String(validate=validate.Length(min=1, max=100))
    numero_documento = fields.String(validate=validate.Length(min=1, max=50))
    email = fields.Email(validate=validate.Length(max=255))
    phone = fields.String(allow_none=True, validate=validate.Length(max=15))
    cargo = fields.String(allow_none=True, validate=validate.Length(max=150))
    unidad = fields.String(allow_none=True, validate=validate.Length(max=150))
    observaciones = fields.String(allow_none=True)
    foto_perfil = fields.String(allow_none=True, validate=validate.Length(max=500))
    # Compatibilidad con formularios anteriores; el rol no se modifica aquí.
    role = fields.Enum(
        Role,
        by_value=True,
        load_only=True,
        validate=validate.OneOf([Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO]),
    )


class UserStatusSchema(Schema):
    status = fields.Enum(UserStatus, by_value=True, required=True)
