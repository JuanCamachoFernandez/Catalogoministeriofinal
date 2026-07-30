from ..errores import error


def registrar_errores_jwt(jwt):
    @jwt.unauthorized_loader
    def token_ausente(_mensaje):
        return error("Autenticación requerida", 401)

    @jwt.invalid_token_loader
    def token_invalido(_mensaje):
        return error("Token inválido", 401)

    @jwt.expired_token_loader
    def token_expirado(_cabecera, _contenido):
        return error("Token expirado", 401)

    @jwt.revoked_token_loader
    def token_revocado(_cabecera, _contenido):
        return error("Sesión revocada", 401)
