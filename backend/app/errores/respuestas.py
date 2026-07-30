from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException


def error(message, status=400, details=None):
    payload = {"error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def registrar_manejadores_errores(app):
    @app.errorhandler(HTTPException)
    def manejar_error_http(exc):
        if not request.path.startswith("/api/"):
            return exc
        return error(exc.description or "Solicitud inválida", exc.code or 500)

    @app.errorhandler(Exception)
    def manejar_error_inesperado(exc):
        if not request.path.startswith("/api/"):
            raise exc
        current_app.logger.exception("Error no controlado en la API")
        if current_app.config.get("TESTING"):
            raise exc
        return error("Error interno del servidor", 500)

    @app.errorhandler(422)
    def manejar_entidad_invalida(_exc):
        return error("Datos inválidos", 422)
