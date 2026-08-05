from pathlib import Path
from urllib.parse import urlparse
import uuid
from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
UPLOAD_PREFIX = "/uploads/"
CLOUDINARY_ROOT_FOLDER = "catalogo-ministerio"


class _TestingCloudinaryUploader:
    @staticmethod
    def upload(_stream, **kwargs):
        public_id = f"{kwargs['folder']}/{kwargs['public_id']}"
        return {
            "secure_url": f"https://res.cloudinary.com/testing/image/upload/v1/{public_id}.png",
            "public_id": public_id,
        }

    @staticmethod
    def destroy(_public_id, **_kwargs):
        return {"result": "ok"}


def _cloudinary_uploader():
    if current_app.config.get("TESTING"):
        return _TestingCloudinaryUploader
    try:
        import cloudinary
        import cloudinary.uploader
    except ModuleNotFoundError as exc:
        raise ValueError("No fue posible subir la imagen") from exc
    config = cloudinary.config()
    if not all((config.cloud_name, config.api_key, config.api_secret)):
        return None
    return cloudinary.uploader


def _validate_image_file(file):
    if not file or not file.filename:
        return None
    if "." not in file.filename:
        raise ValueError("Formato de imagen no permitido")

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato de imagen no permitido")

    try:
        image = Image.open(file.stream)
        image.verify()
        file.stream.seek(0)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("El archivo no es una imagen válida") from exc

    return extension


def cloudinary_folder(folder):
    return f"{CLOUDINARY_ROOT_FOLDER}/{folder}"


def is_managed_upload_url(url, folder=None):
    if not url or not url.startswith(UPLOAD_PREFIX):
        return False
    relative = url.removeprefix(UPLOAD_PREFIX)
    return not folder or relative.startswith(f"{folder}/")


def is_our_cloudinary_url(url, folder=None):
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "res.cloudinary.com":
        return False
    if "/image/upload/" not in parsed.path:
        return False
    expected_folder = cloudinary_folder(folder) if folder else CLOUDINARY_ROOT_FOLDER
    return f"/{expected_folder}/" in parsed.path


def cloudinary_public_id_from_url(url, folder=None):
    if not is_our_cloudinary_url(url, folder):
        return None
    parsed = urlparse(url)
    marker = "/image/upload/"
    tail = parsed.path.split(marker, 1)[-1]
    segments = [segment for segment in tail.split("/") if segment]
    while segments and (
        segments[0].startswith("v") and segments[0][1:].isdigit()
        or "," in segments[0]
    ):
        segments.pop(0)
    if not segments:
        return None
    public_id = "/".join(segments)
    filename = public_id.rsplit("/", 1)[-1]
    if "." in filename:
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension in ALLOWED_EXTENSIONS:
            public_id = public_id[: -(len(extension) + 1)]
    expected_prefix = cloudinary_folder(folder) if folder else CLOUDINARY_ROOT_FOLDER
    return public_id if public_id.startswith(expected_prefix) else None


def validate_image_reference(url, folder, *, allow_none=False):
    if not url:
        if allow_none:
            return None
        raise ValueError("La imagen debe subirse primero")
    if is_managed_upload_url(url, folder):
        require_managed_upload(url, folder)
        return "managed"
    if is_our_cloudinary_url(url, folder):
        return "cloudinary"
    raise ValueError("La imagen debe subirse primero")


def upload_to_cloudinary(file, folder):
    extension = _validate_image_file(file)
    if not extension:
        return None

    filename = secure_filename(file.filename)
    identifier = uuid.uuid4().hex

    uploader = _cloudinary_uploader()
    if uploader is None:
        local_url = save_upload(file, folder)
        return {
            "url": local_url,
            "public_id": None,
            "filename": filename,
        }

    try:
        result = uploader.upload(
            file.stream,
            folder=cloudinary_folder(folder),
            public_id=identifier,
            resource_type="image",
            overwrite=False,
        )
    except Exception as exc:
        raise ValueError("No fue posible subir la imagen") from exc

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "filename": filename,
    }


def delete_cloudinary_upload(public_id):
    if not public_id:
        return

    _cloudinary_uploader().destroy(
        public_id,
        resource_type="image",
        invalidate=True,
    )


def save_upload(file, folder):
    extension = _validate_image_file(file)
    if not extension:
        return None
    name = secure_filename(f"{uuid.uuid4().hex}.{extension}")
    target = Path(current_app.config["CARPETA_CARGAS"]) / folder
    target.mkdir(parents=True, exist_ok=True)
    file.save(target / name)
    return f"{UPLOAD_PREFIX}{folder}/{name}"


def managed_upload_path(url, expected_folder=None):
    if not is_managed_upload_url(url, expected_folder):
        return None
    relative = url.removeprefix(UPLOAD_PREFIX)
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
