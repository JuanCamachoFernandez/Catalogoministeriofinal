from ..extensiones import db
from ..modelos import RegistrationRequest, RegistrationStatus, Role, UserStatus
from ..repositorios.usuarios import obtener_unidad_activa_usuario


def puede_recuperar_contrasena(usuario):
    if not usuario or usuario.deleted_at or usuario.status != UserStatus.ACTIVE:
        return False
    if usuario.role != Role.PRODUCTIVE_UNIT_RESPONSIBLE:
        return True
    unidad = obtener_unidad_activa_usuario(usuario.id)
    if not unidad:
        return False
    solicitud = db.session.get(RegistrationRequest, unidad.registration_request_id)
    return bool(solicitud and solicitud.estado == RegistrationStatus.APPROVED)


def contrasena_segura(valor):
    return len(valor) >= 10 and all(
        (
            any(caracter.isupper() for caracter in valor),
            any(caracter.islower() for caracter in valor),
            any(caracter.isdigit() for caracter in valor),
            any(not caracter.isalnum() for caracter in valor),
        )
    )
