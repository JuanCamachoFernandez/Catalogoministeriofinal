from flask import current_app, send_from_directory


def estado_salud():
    return {"status": "ok"}


def servir_archivo_publico(name):
    carpeta = name.replace("\\", "/").split("/", 1)[0]
    if carpeta not in current_app.config["CARPETAS_PUBLICAS_CARGAS"]:
        return {"error": "Archivo no disponible"}, 404
    return send_from_directory(current_app.config["CARPETA_CARGAS"], name)
