import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "solo-desarrollo")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "solo-desarrollo-jwt")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql+psycopg://catalogo:catalogo@localhost:5432/catalogo_ferias")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    UPLOAD_FOLDER = str(BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))
