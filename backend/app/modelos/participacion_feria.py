from sqlalchemy import UniqueConstraint, select

from ..extensiones import db
from .base import TimestampMixin, now, uid
from .enumeraciones import AssignmentStatus


class FairParticipation(TimestampMixin, db.Model):
    __tablename__ = "participaciones_feria"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    fair_id = db.Column(db.Uuid, db.ForeignKey("ferias.id"), nullable=False, index=True)
    productive_unit_id = db.Column(
        db.Uuid, db.ForeignKey("unidades_productivas.id"), nullable=False, index=True
    )
    estado = db.Column(
        db.Enum(AssignmentStatus, name="estado_participacion_feria"),
        nullable=False,
        default=AssignmentStatus.PENDING,
        index=True,
    )
    observaciones = db.Column(db.Text)
    authorized_by = db.Column(db.Uuid, db.ForeignKey("usuarios.id"))
    authorized_at = db.Column(db.DateTime(timezone=True))
    revoked_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("fair_id", "productive_unit_id", name="participacion_feria_unica"),
    )

    @classmethod
    def for_fair_query(cls, fair_id):
        return select(cls).where(
            cls.fair_id == fair_id,
            cls.estado.notin_([AssignmentStatus.REVOKED, AssignmentStatus.INACTIVE]),
        )
