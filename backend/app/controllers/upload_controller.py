from flask import Blueprint, request

from ..models import Role
from ..views import error
from .common import current_user, roles, save_upload

upload_bp = Blueprint("uploads", __name__)


@upload_bp.post("/uploads")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.EXPOSITOR)
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
        url = save_upload(request.files.get("file"), folder)
    except ValueError as exc:
        return error(str(exc))
    if not url:
        return error("Debe enviar un archivo")
    return {"url": url}, 201
