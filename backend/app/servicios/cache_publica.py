from time import monotonic

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..extensiones import db
from ..modelos import CacheState

PUBLIC_CACHE = {}
PUBLIC_CACHE_KEY = "catalogo_publico"


def public_cache_version():
    try:
        state = db.session.scalar(select(CacheState).where(CacheState.key == PUBLIC_CACHE_KEY))
        return state.version if state else 0
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("La caché pública no está disponible")
        return None


def invalidate_public_cache():
    PUBLIC_CACHE.clear()
    try:
        state = db.session.scalar(
            select(CacheState).where(CacheState.key == PUBLIC_CACHE_KEY).with_for_update()
        )
        if state:
            state.version += 1
        else:
            db.session.add(CacheState(key=PUBLIC_CACHE_KEY, version=1))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("No se pudo invalidar la versión de caché pública")


def get_public_cache(key):
    cached = PUBLIC_CACHE.get(key)
    if not cached:
        return None
    version, expires_at, value = cached
    current_version = public_cache_version()
    if current_version is None or version != current_version or expires_at <= monotonic():
        PUBLIC_CACHE.pop(key, None)
        return None
    return value


def set_public_cache(key, value):
    ttl = current_app.config["SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA"]
    version = public_cache_version()
    if version is not None:
        PUBLIC_CACHE[key] = (version, monotonic() + ttl, value)
    return value
