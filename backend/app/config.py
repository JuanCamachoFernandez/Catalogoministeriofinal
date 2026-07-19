import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    # Flask y sus extensiones exigen estas claves internas; sus variables de
    # entorno, que son las que configura el usuario, se mantienen en español.
    SECRET_KEY = os.getenv("CLAVE_SECRETA_APLICACION", "solo-desarrollo")
    JWT_SECRET_KEY = os.getenv("CLAVE_SECRETA_SESIONES", "solo-desarrollo-jwt")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DIRECCION_BASE_DATOS",
        "postgresql+psycopg://catalogo:catalogo@localhost:5432/catalogo_ferias",
    )
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
