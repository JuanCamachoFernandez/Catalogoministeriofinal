from functools import wraps

from flask import g, request
from marshmallow import ValidationError

from ..errores import error


def validate_json(schema):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                g.validated_json = schema.load(request.get_json(silent=True) or {})
            except ValidationError as exc:
                return error("Datos inválidos", 400, exc.messages)
            return function(*args, **kwargs)

        return wrapped

    return decorator


def validated_json():
    return g.validated_json
