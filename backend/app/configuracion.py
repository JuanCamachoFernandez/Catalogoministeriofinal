import os
import secrets
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
ENTORNO_APLICACION = os.getenv("ENTORNO_APLICACION", "desarrollo").lower()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _development_secret(env_name: str, prefix: str) -> str | None:
    configured = os.getenv(env_name)
    if configured or ENTORNO_APLICACION == "produccion":
        return configured
    return f"{prefix}-{secrets.token_urlsafe(32)}"


def database_uri() -> str:
    uri = os.getenv("DIRECCION_BASE_DATOS") or os.getenv("DATABASE_URL")
    if not uri:
        return "postgresql+psycopg://catalogo:catalogo@localhost:5432/catalogo_ferias"
    if uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql+psycopg://", 1)
    if uri.startswith("postgresql://"):
        return uri.replace("postgresql://", "postgresql+psycopg://", 1)
    return uri


class Config:
    # Flask y sus extensiones exigen estas claves internas; sus variables de
    # entorno, que son las que configura el usuario, se mantienen en español.
    SECRET_KEY = _development_secret("CLAVE_SECRETA_APLICACION", "solo-desarrollo")
    JWT_SECRET_KEY = _development_secret("CLAVE_SECRETA_SESIONES", "solo-desarrollo-jwt")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    LIMITE_INTENTOS_FALLIDOS = int(os.getenv("LIMITE_INTENTOS_FALLIDOS", 5))
    MINUTOS_BLOQUEO = int(os.getenv("MINUTOS_BLOQUEO", 15))
    SEGUNDOS_ENTRE_INTENTOS_RECUPERACION = int(
        os.getenv("SEGUNDOS_ENTRE_INTENTOS_RECUPERACION", 60)
    )
    DIAS_RETENCION_SOLICITUDES_RECHAZADAS = int(
        os.getenv("DIAS_RETENCION_SOLICITUDES_RECHAZADAS", 30)
    )
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DIRECCION_INTERFAZ_WEB = os.getenv("DIRECCION_INTERFAZ_WEB", "http://localhost:5173")
    ORIGENES_PERMITIDOS = _split_csv(
        os.getenv("ORIGENES_PERMITIDOS", DIRECCION_INTERFAZ_WEB)
    )
    CARPETA_CARGAS = str(BASE_DIR / os.getenv("CARPETA_CARGAS", "uploads"))
    MAX_FILE_UPLOAD_SIZE = 10 * 1024 * 1024
    MAX_MULTIPART_OVERHEAD = 2 * 1024 * 1024
    MAX_CONTENT_LENGTH = max(
        int(
            os.getenv(
                "TAMANO_MAXIMO_CONTENIDO",
                MAX_FILE_UPLOAD_SIZE + MAX_MULTIPART_OVERHEAD,
            )
        ),
        MAX_FILE_UPLOAD_SIZE + MAX_MULTIPART_OVERHEAD,
    )
    SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA = int(
        os.getenv("SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA", 60)
    )
    ENTORNO_APLICACION = ENTORNO_APLICACION
    DEBUG = ENTORNO_APLICACION == "desarrollo" and os.getenv("FLASK_DEBUG") == "1"
    MOSTRAR_CREDENCIALES_TEMPORALES = (
        ENTORNO_APLICACION != "produccion"
        and os.getenv(
            "MOSTRAR_CREDENCIALES_TEMPORALES",
            "true" if os.getenv("PYTEST_CURRENT_TEST") else "false",
        ).lower()
        == "true"
    )
    CARPETAS_PUBLICAS_CARGAS = frozenset(
        {
            "ferias",
            "general",
            "logos",
            "perfiles",
            "productos",
            "solicitudes",
            "unidades_productivas",
        }
    )


def validar_configuracion_segura(app) -> None:
    """Impide iniciar producción con secretos o base de datos conocidos."""
    if app.config.get("TESTING") or app.config.get("ENTORNO_APLICACION") != "produccion":
        return

    inseguros = {
        "SECRET_KEY": {None, ""},
        "JWT_SECRET_KEY": {None, ""},
    }
    faltantes = [
        clave for clave, valores in inseguros.items() if app.config.get(clave) in valores
    ]
    uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if "catalogo:catalogo@localhost" in uri:
        faltantes.append("SQLALCHEMY_DATABASE_URI")
    origins = app.config.get("ORIGENES_PERMITIDOS") or []
    if not origins or any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
        faltantes.append("ORIGENES_PERMITIDOS")
    if not os.getenv("CLOUDINARY_URL", "").strip():
        faltantes.append("CLOUDINARY_URL")
    if os.getenv("ENVIO_CORREO_HABILITADO", "false").lower() == "true":
        if not os.getenv("CLAVE_BREVO", "").strip():
            faltantes.append("CLAVE_BREVO")
        if not os.getenv("CORREO_REMITENTE_BREVO", "").strip():
            faltantes.append("CORREO_REMITENTE_BREVO")
    if faltantes:
        raise RuntimeError(
            "Configuración insegura para producción: " + ", ".join(sorted(faltantes))
        )
