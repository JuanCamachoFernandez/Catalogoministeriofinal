from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
import uuid

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
UPLOAD_PREFIX = "/uploads/"
CLOUDINARY_ROOT_FOLDER = "catalogo-ministerio"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
WEBP_QUALITY = 82

IMAGE_VARIANTS = {
    "fair_cover": {"max_size": (1600, 1600)},
    "generic": {"max_size": None},
    "product": {"max_size": (1600, 1600)},
    "profile_photo": {"max_size": None},
    "unit_logo": {"max_size": (1000, 1000)},
}
FOLDER_IMAGE_VARIANTS = {
    "ferias": "fair_cover",
    "logos": "unit_logo",
    "perfiles": "profile_photo",
    "productos": "product",
}


class _TestingCloudinaryUploader:
    @staticmethod
    def upload(_stream, **kwargs):
        public_id = f"{kwargs['folder']}/{kwargs['public_id']}"
        return {
            "secure_url": f"https://res.cloudinary.com/testing/image/upload/v1/{public_id}.webp",
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


def _file_size(stream):
    position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(position)
    return size


def _resolve_image_variant(folder, image_variant=None):
    variant = image_variant or FOLDER_IMAGE_VARIANTS.get(folder, "generic")
    if variant not in IMAGE_VARIANTS:
        raise ValueError("Configuracion de imagen no soportada")
    return variant


def _normalize_for_webp(image):
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _optimize_image(file, image_variant):
    if not file or not file.filename:
        return None
    if "." not in file.filename:
        raise ValueError("Formato de imagen no permitido")

    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato de imagen no permitido")
    if _file_size(file.stream) > MAX_IMAGE_BYTES:
        raise ValueError("La imagen no puede superar los 10 MB")

    try:
        file.stream.seek(0)
        image = Image.open(file.stream)
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("El archivo no es una imagen valida") from exc

    try:
        optimized = ImageOps.exif_transpose(image)
    except OSError as exc:
        raise ValueError("El archivo no es una imagen valida") from exc

    max_size = IMAGE_VARIANTS[image_variant]["max_size"]
    if max_size:
        optimized.thumbnail(max_size, Image.Resampling.LANCZOS)
    optimized = _normalize_for_webp(optimized)

    output = BytesIO()
    optimized.save(output, format="WEBP", quality=WEBP_QUALITY, method=6)
    output.seek(0)

    filename_base = secure_filename(file.filename.rsplit(".", 1)[0]) or "imagen"
    return {
        "filename": f"{filename_base}.webp",
        "stream": output,
    }


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


def upload_to_cloudinary(file, folder, image_variant=None):
    variant = _resolve_image_variant(folder, image_variant)
    optimized = _optimize_image(file, variant)
    if not optimized:
        return None

    filename = optimized["filename"]
    identifier = uuid.uuid4().hex

    uploader = _cloudinary_uploader()
    if uploader is None:
        local_url = save_upload(
            file,
            folder,
            image_variant=variant,
            processed=optimized,
        )
        return {
            "url": local_url,
            "public_id": None,
            "filename": filename,
        }

    try:
        result = uploader.upload(
            optimized["stream"],
            folder=cloudinary_folder(folder),
            public_id=identifier,
            resource_type="image",
            overwrite=False,
            format="webp",
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


def save_upload(file, folder, image_variant=None, processed=None):
    variant = _resolve_image_variant(folder, image_variant)
    optimized = processed or _optimize_image(file, variant)
    if not optimized:
        return None
    name = secure_filename(f"{uuid.uuid4().hex}.webp")
    target = Path(current_app.config["CARPETA_CARGAS"]) / folder
    target.mkdir(parents=True, exist_ok=True)
    with (target / name).open("wb") as saved_file:
        saved_file.write(optimized["stream"].getvalue())
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
