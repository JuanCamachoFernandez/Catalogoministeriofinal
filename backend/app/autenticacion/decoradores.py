from functools import wraps

from flask_jwt_extended import jwt_required

from ..errores import error
from ..modelos import UserStatus
from .sesiones import usuario_actual


def roles(*permitidos):
    """Protege una operación usando el rol persistido, nunca el enviado por el cliente."""

    def decorador(funcion):
        @wraps(funcion)
        @jwt_required()
        def envuelta(*args, **kwargs):
            usuario = usuario_actual()
            if not usuario or usuario.deleted_at or usuario.status != UserStatus.ACTIVE:
                return error("Cuenta no disponible", 403)
            if usuario.must_change_password:
                return error("Debe cambiar su contraseña", 403)
            if usuario.role not in permitidos:
                return error("No autorizado", 403)
            return funcion(*args, **kwargs)

        return envuelta

    return decorador
