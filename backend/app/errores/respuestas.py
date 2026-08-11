from flask import current_app, jsonify, request
from werkzeug.exceptions import HTTPException


HTTP_ERROR_MESSAGES = {
    400: "Solicitud inválida",
    401: "Autenticación requerida",
    403: "No autorizado",
    404: "Recurso no encontrado",
    405: "Método no permitido",
    413: "El contenido enviado excede el tamaño permitido",
    422: "Datos inválidos",
    429: "Demasiadas solicitudes",
    500: "Error interno del servidor",
}


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
        status = exc.code or 500
        return error(HTTP_ERROR_MESSAGES.get(status, "Error en la solicitud"), status)

    @app.errorhandler(Exception)
    def manejar_error_inesperado(exc):
        if not request.path.startswith("/api/"):
            raise exc
        current_app.logger.exception("Error no controlado en la API")
        if current_app.config.get("TESTING"):
            raise exc
        return error(HTTP_ERROR_MESSAGES[500], 500)
