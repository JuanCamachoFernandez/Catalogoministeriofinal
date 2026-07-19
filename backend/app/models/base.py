import uuid
from datetime import datetime, timezone

from ..extensions import db


def now():
    return datetime.now(timezone.utc)


def uid():
    return uuid.uuid4()


class TimestampMixin:
    created_at = db.Column(
        "fecha_creacion", db.DateTime(timezone=True), nullable=False, default=now
    )
    updated_at = db.Column(
        "fecha_actualizacion",
        db.DateTime(timezone=True),
        nullable=False,
        default=now,
        onupdate=now,
    )
