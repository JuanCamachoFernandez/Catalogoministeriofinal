from sqlalchemy import Index, UniqueConstraint, select

from ..extensiones import db
from .base import TimestampMixin, uid
from .enumeraciones import SectorStatus


class ProductiveSector(TimestampMixin, db.Model):
    __tablename__ = "sectores_productivos"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    estado = db.Column(
        db.Enum(SectorStatus, name="estado_sector_productivo"),
        nullable=False,
        default=SectorStatus.ACTIVE,
        index=True,
    )
    es_otro = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column("fecha_eliminacion", db.DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("nombre"),
        Index("indice_sectores_productivos_nombre", "nombre"),
    )

    @classmethod
    def active_query(cls):
        return select(cls).where(
            cls.estado == SectorStatus.ACTIVE, cls.deleted_at.is_(None)
        ).order_by(cls.nombre)
