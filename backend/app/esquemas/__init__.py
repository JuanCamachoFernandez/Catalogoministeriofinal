"""Esquemas de entrada agrupados por dominio.

Las reexportaciones mantienen concisos los imports de las rutas mientras los
serializadores, validadores y respuestas de error viven en sus propias capas.
"""

from ..errores import error
from ..serializadores import (
    admin_user_json,
    assignment_json,
    exhibitor_json,
    fair_json,
    paginate,
    product_json,
    user_json,
)
from ..validadores import validate_json, validated_json

__all__ = [
    "admin_user_json",
    "assignment_json",
    "error",
    "exhibitor_json",
    "fair_json",
    "product_json",
    "paginate",
    "user_json",
    "validate_json",
    "validated_json",
]
