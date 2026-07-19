from marshmallow import Schema, fields, validate


password = fields.String(required=True, validate=validate.Length(min=10, max=256))


class LoginSchema(Schema):
    login = fields.String(required=True, validate=validate.Length(min=1, max=255))
    password = fields.String(required=True, load_only=True)


class ChangePasswordSchema(Schema):
    current_password = fields.String(required=True, load_only=True)
    new_password = password


class ReauthenticateSchema(Schema):
    current_password = fields.String(required=True, load_only=True)


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=255))


class VerifyRecoveryCodeSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=255))
    code = fields.String(
        required=True,
        validate=validate.Regexp(r"^\d{6}$", error="Ingrese los 6 números del código"),
    )


class ResetPasswordSchema(Schema):
    token = fields.String(required=True, validate=validate.Length(min=20, max=256))
    new_password = password
