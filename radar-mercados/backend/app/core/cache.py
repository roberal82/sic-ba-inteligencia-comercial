"""Cache con TTL. Usa Redis si REDIS_URL esta configurado y accesible; si no, cae a memoria de proceso."""
import json
import time
from typing import Any

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

_memory_store: dict[str, tuple[float, Any]] = {}
_redis_client = None

if settings.redis_url:
    try:
        import redis as redis_lib

        _redis_client = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        _redis_client.ping()
        logger.info("Cache Redis conectado en {}", settings.redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis no disponible ({}). Usando cache en memoria.", exc)
        _redis_client = None


def cache_get(key: str) -> Any | None:
    if _redis_client is not None:
        try:
            raw = _redis_client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fallo lectura Redis para {}: {}", key, exc)
    entry = _memory_store.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        _memory_store.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    ttl = ttl_seconds if ttl_seconds is not None else settings.cache_ttl_seconds
    if _redis_client is not None:
        try:
            _redis_client.setex(key, ttl, json.dumps(value, default=str))
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fallo escritura Redis para {}: {}", key, exc)
    _memory_store[key] = (time.time() + ttl, value)


def cache_clear() -> None:
    _memory_store.clear()
    if _redis_client is not None:
        try:
            _redis_client.flushdb()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fallo al limpiar Redis: {}", exc)


def cache_backend_name() -> str:
    return "redis" if _redis_client is not None else "memoria"
