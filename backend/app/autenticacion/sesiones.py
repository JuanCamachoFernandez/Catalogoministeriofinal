import uuid

from flask_jwt_extended import get_jwt_identity

from ..extensiones import db
from ..modelos import User


def usuario_actual():
    """Obtiene siempre el usuario y su rol desde la base de datos."""
    try:
        identity = get_jwt_identity()
    except RuntimeError:
        return None
    try:
        user_id = uuid.UUID(identity)
    except (ValueError, TypeError, AttributeError):
        return None
    return db.session.get(User, user_id)


current_user = usuario_actual
