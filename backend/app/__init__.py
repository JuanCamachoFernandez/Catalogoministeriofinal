import os

from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS

from .config import Config
from .extensions import db, jwt, migrate


def create_app(config=Config):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config)
    os.makedirs(app.config["CARPETA_CARGAS"], exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, origins=app.config["ORIGENES_PERMITIDOS"])

    from .controllers import register_controllers
    from .controllers.common import PUBLIC_CACHE
    from .models import RevokedToken, User, UserStatus

    # La caché vive en memoria del proceso. Al crear otra instancia de Flask
    # (pruebas, recarga del servidor o un worker nuevo) no debe reutilizar
    # respuestas asociadas a una base o configuración anterior.
    PUBLIC_CACHE.clear()
    register_controllers(app)

    @jwt.token_in_blocklist_loader
    def token_revoked(_header, payload):
        if db.session.scalar(
            db.select(RevokedToken.id).where(RevokedToken.jti == payload["jti"])
        ) is not None:
            return True
        try:
            import uuid
            user = db.session.get(User, uuid.UUID(payload["sub"]))
        except (ValueError, TypeError):
            return True
        return (
            not user
            or user.deleted_at is not None
            or user.status != UserStatus.ACTIVE
            or payload.get("ver", 0) != user.token_version
        )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/uploads/<path:name>")
    def uploads(name):
        return send_from_directory(app.config["CARPETA_CARGAS"], name)

    from .commands import register_commands

    register_commands(app)
    return app
