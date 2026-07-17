from ..extensions import db
from .base import now, uid


class Audit(db.Model):
    __tablename__ = "audits"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column(db.Uuid, db.ForeignKey("users.id"), index=True)
    accion = db.Column(db.String(100), nullable=False, index=True)
    entidad = db.Column(db.String(100), nullable=False)
    entidad_id = db.Column(db.Uuid)
    descripcion = db.Column(db.Text)
    datos_anteriores = db.Column(db.JSON)
    datos_nuevos = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False, index=True)
