from ..extensions import db


class CacheState(db.Model):
    __tablename__ = "estados_memoria_temporal"
    key = db.Column("clave", db.String(80), primary_key=True)
    version = db.Column("version", db.BigInteger, nullable=False, default=0)
