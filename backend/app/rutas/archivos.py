from flask import Blueprint, request

from ..modelos import Role
from ..esquemas import error
from ..servicios import upload_to_cloudinary

from ..autenticacion.decoradores import roles
from ..autenticacion.sesiones import current_user
from ..autenticacion.permisos import ROLES_GESTION_COMPARTIDA_LEGADA
upload_bp = Blueprint("uploads", __name__)


@upload_bp.post("/uploads")
@roles(*ROLES_GESTION_COMPARTIDA_LEGADA)
def upload_file():
    folder = request.form.get("folder", "general")
    allowed = {
        Role.SUPERADMIN: {"general", "ferias", "productos", "logos", "perfiles"},
        Role.ADMIN_VICEMINISTERIO: {"general", "ferias", "productos", "logos", "perfiles"},
        Role.EXPOSITOR: {"productos", "logos"},
    }
    if folder not in allowed[current_user().role]:
        return error("No autorizado para esta carpeta", 403)
    try:
        uploaded = upload_to_cloudinary(request.files.get("file"), folder)
    except ValueError as exc:
        return error(str(exc))
    if not uploaded:
        return error("Debe enviar un archivo")
    return {"url": uploaded["url"]}, 201
