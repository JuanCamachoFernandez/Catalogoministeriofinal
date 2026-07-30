import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from .configuracion import Config, validar_configuracion_segura
from .controladores.sistema import estado_salud, servir_archivo_publico
from .errores import registrar_manejadores_errores
from .extensiones import db, jwt, migrate
from .autenticacion.errores import registrar_errores_jwt


def create_app(config=Config):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config)
    validar_configuracion_segura(app)
    os.makedirs(app.config["CARPETA_CARGAS"], exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    registrar_errores_jwt(jwt)
    CORS(app, origins=app.config["ORIGENES_PERMITIDOS"])
    registrar_manejadores_errores(app)

    from .rutas import registrar_rutas
    from .servicios import PUBLIC_CACHE
    from .modelos import RevokedToken, User, UserStatus

    # La caché vive en memoria del proceso. Al crear otra instancia de Flask
    # (pruebas, recarga del servidor o un worker nuevo) no debe reutilizar
    # respuestas asociadas a una base o configuración anterior.
    PUBLIC_CACHE.clear()
    registrar_rutas(app)

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

    app.add_url_rule("/api/health", endpoint="health", view_func=estado_salud)
    app.add_url_rule(
        "/uploads/<path:name>", endpoint="uploads", view_func=servir_archivo_publico
    )

    from .comandos import registrar_comandos

    registrar_comandos(app)
    return app
