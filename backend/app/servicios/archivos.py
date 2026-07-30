from pathlib import Path
import uuid

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def save_upload(file, folder):
    if not file or not file.filename:
        return None
    extension = file.filename.rsplit(".", 1)[-1].lower()
    if "." not in file.filename or extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato de imagen no permitido")
    try:
        image = Image.open(file.stream)
        image.verify()
        file.stream.seek(0)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("El archivo no es una imagen válida") from exc
    name = secure_filename(f"{uuid.uuid4().hex}.{extension}")
    target = Path(current_app.config["CARPETA_CARGAS"]) / folder
    target.mkdir(parents=True, exist_ok=True)
    file.save(target / name)
    return f"/uploads/{folder}/{name}"


def managed_upload_path(url, expected_folder=None):
    if not url or not url.startswith("/uploads/"):
        return None
    relative = url.removeprefix("/uploads/")
    if expected_folder and not relative.startswith(f"{expected_folder}/"):
        return None
    root = Path(current_app.config["CARPETA_CARGAS"]).resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def require_managed_upload(url, folder):
    path = managed_upload_path(url, folder)
    if not path or not path.is_file():
        raise ValueError(f"La imagen debe subirse primero en la carpeta {folder}")
    return path


def delete_managed_upload(url, folder=None):
    path = managed_upload_path(url, folder)
    if path and path.is_file():
        path.unlink()
