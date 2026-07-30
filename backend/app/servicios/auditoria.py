from flask import has_request_context, request

from ..autenticacion.sesiones import current_user
from ..extensiones import db
from ..modelos import Audit

AUDIT_ACTION_DESCRIPTIONS = {
    "CREAR": "Creación", "EDITAR": "Edición", "ELIMINAR": "Eliminación",
    "RESTAURAR": "Restauración", "CAMBIAR_ESTADO": "Cambio de estado",
    "SINCRONIZAR_ESTADO": "Sincronización automática del estado",
    "AGREGAR_IMAGEN": "Adición de imagen", "EDITAR_IMAGEN": "Edición de imagen",
    "ELIMINAR_IMAGEN": "Eliminación de imagen", "ASIGNAR": "Asignación",
    "AUTORIZAR": "Autorización", "REVOCAR": "Revocación", "BLOQUEAR": "Bloqueo",
    "DESBLOQUEAR": "Desbloqueo", "CAMBIAR_CONTRASENA": "Cambio de contraseña",
    "RESTABLECER_CONTRASENA": "Restablecimiento de contraseña",
    "CREAR_SOLICITUD": "Creación", "APROBAR_SOLICITUD": "Aprobación",
    "RECHAZAR_SOLICITUD": "Rechazo", "ENVIAR_CREDENCIALES": "Envío de credenciales",
    "REENVIAR_CREDENCIALES": "Reenvío de credenciales",
    "ENVIAR_RECHAZO": "Envío de notificación de rechazo",
    "ENVIAR_RECUPERACION": "Envío de recuperación de contraseña",
    "INTENTO_RECUPERACION_FALLIDO": "Intento de recuperación fallido",
    "GENERAR_REPORTE": "Generación de reporte",
}
AUDIT_ENTITY_DESCRIPTIONS = {
    "RegistrationRequest": "solicitud de registro", "ProductiveUnit": "Unidad Productiva",
    "ProductiveSector": "Sector Productivo", "FairParticipation": "participación en feria",
    "FeriaExpositor": "participación de expositor", "Fair": "feria", "Product": "producto",
    "Usuario": "usuario", "Perfil": "perfil", "Unidad": "unidad administrativa",
    "Categoria": "categoría", "Producto": "producto", "Feria": "feria",
    "Expositor": "expositor", "Reporte": "reporte",
}


def audit_description(action, entity):
    action_text = AUDIT_ACTION_DESCRIPTIONS.get(action, (action or "Acción").replace("_", " ").capitalize())
    entity_text = AUDIT_ENTITY_DESCRIPTIONS.get(entity, (entity or "registro").replace("_", " ").lower())
    return f"{action_text} de {entity_text}"


def _safe_audit_value(value):
    sensitive = {"password", "contrasena", "contraseña", "token", "secret", "clave"}
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if any(term in key.lower() for term in sensitive) else _safe_audit_value(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_audit_value(item) for item in value]
    return value


def audit(action, entity, entity_id=None, description=None, before=None, after=None, actor_user_id=None, result="SUCCESS"):
    user = current_user() if has_request_context() else None
    db.session.add(Audit(
        user_id=actor_user_id if actor_user_id is not None else (user.id if user else None),
        accion=action, entidad=entity, entidad_id=entity_id,
        descripcion=(description or "").strip() or audit_description(action, entity),
        datos_anteriores=_safe_audit_value(before), datos_nuevos=_safe_audit_value(after),
        ip_address=request.remote_addr if has_request_context() else None,
        user_agent=(request.user_agent.string[:500] if has_request_context() else None),
        resultado=result,
    ))
