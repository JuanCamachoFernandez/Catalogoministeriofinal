import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


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
    SECRET_KEY = os.getenv("CLAVE_SECRETA_APLICACION", "solo-desarrollo")
    JWT_SECRET_KEY = os.getenv("CLAVE_SECRETA_SESIONES", "solo-desarrollo-jwt")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    LIMITE_INTENTOS_FALLIDOS = int(os.getenv("LIMITE_INTENTOS_FALLIDOS", 5))
    MINUTOS_BLOQUEO = int(os.getenv("MINUTOS_BLOQUEO", 15))
    DIAS_RETENCION_SOLICITUDES_RECHAZADAS = int(
        os.getenv("DIAS_RETENCION_SOLICITUDES_RECHAZADAS", 30)
    )
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DIRECCION_INTERFAZ_WEB = os.getenv("DIRECCION_INTERFAZ_WEB", "http://localhost:5173")
    ORIGENES_PERMITIDOS = os.getenv("ORIGENES_PERMITIDOS", "http://localhost:5173").split(",")
    CARPETA_CARGAS = str(BASE_DIR / os.getenv("CARPETA_CARGAS", "uploads"))
    MAX_CONTENT_LENGTH = int(
        os.getenv("TAMANO_MAXIMO_CONTENIDO", 10 * 1024 * 1024)
    )
    SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA = int(
        os.getenv("SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA", 60)
    )
    ENTORNO_APLICACION = os.getenv("ENTORNO_APLICACION", "desarrollo").lower()
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
        "SECRET_KEY": {None, "", "solo-desarrollo"},
        "JWT_SECRET_KEY": {None, "", "solo-desarrollo-jwt"},
    }
    faltantes = [
        clave for clave, valores in inseguros.items() if app.config.get(clave) in valores
    ]
    uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if "catalogo:catalogo@localhost" in uri:
        faltantes.append("SQLALCHEMY_DATABASE_URI")
    if faltantes:
        raise RuntimeError(
            "Configuración insegura para producción: " + ", ".join(sorted(faltantes))
        )
