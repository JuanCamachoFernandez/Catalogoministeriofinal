from ..extensions import db


class CacheState(db.Model):
    __tablename__ = "cache_states"
    key = db.Column(db.String(80), primary_key=True)
    version = db.Column(db.BigInteger, nullable=False, default=0)
