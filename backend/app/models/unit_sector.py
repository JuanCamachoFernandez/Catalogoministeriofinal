from sqlalchemy import CheckConstraint, UniqueConstraint

from ..extensions import db
from .base import TimestampMixin, uid
from .enums import SectorStatus


class UnitSector(TimestampMixin, db.Model):
    __tablename__ = "sectores_unidad"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    productive_unit_id = db.Column(
        db.Uuid, db.ForeignKey("unidades_productivas.id", ondelete="CASCADE"), nullable=False
    )
    productive_sector_id = db.Column(
        db.Uuid, db.ForeignKey("sectores_productivos.id"), nullable=False
    )
    detalle_otro = db.Column(db.String(255))
    estado = db.Column(
        db.Enum(SectorStatus, name="estado_sector_unidad"),
        nullable=False,
        default=SectorStatus.ACTIVE,
    )
    __table_args__ = (
        UniqueConstraint(
            "productive_unit_id", "productive_sector_id", name="sector_unidad_unico"
        ),
        CheckConstraint(
            "detalle_otro IS NULL OR length(trim(detalle_otro)) > 0",
            name="detalle_otro_no_vacio",
        ),
    )
