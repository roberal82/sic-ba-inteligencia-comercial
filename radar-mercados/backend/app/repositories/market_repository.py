"""Agrega los indicadores de todos los servicios de pais/clase de activo y persiste
el ultimo snapshot en la base de datos para que /api/markets tenga historico minimo."""
import asyncio

from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
from app.core.logging import logger
from app.models.models import MarketIndicator
from app.services import (
    argentina_service,
    brazil_service,
    commodities_service,
    crypto_service,
    global_markets_service,
    paraguay_service,
)

CACHE_KEY_ALL_INDICATORS = "indicators:all"

_SERVICES = [
    brazil_service.get_indicators,
    paraguay_service.get_indicators,
    argentina_service.get_indicators,
    global_markets_service.get_indicators,
    commodities_service.get_indicators,
    crypto_service.get_indicators,
]


async def fetch_all_indicators(use_cache: bool = True) -> list[dict]:
    if use_cache:
        cached = cache_get(CACHE_KEY_ALL_INDICATORS)
        if cached is not None:
            return cached

    results = await asyncio.gather(*(svc() for svc in _SERVICES), return_exceptions=True)
    indicators: list[dict] = []
    for svc, result in zip(_SERVICES, results, strict=True):
        if isinstance(result, Exception):
            logger.error("market_repository: servicio {} fallo por completo: {}", svc.__module__, result)
            continue
        indicators.extend(result)

    cache_set(CACHE_KEY_ALL_INDICATORS, indicators)
    return indicators


def persist_indicators(db: Session, indicators: list[dict]) -> None:
    """Guarda un snapshot de los indicadores en la base de datos (append-only, para historico)."""
    for item in indicators:
        record = MarketIndicator(**{k: v for k, v in item.items() if k != "id"})
        db.add(record)
    db.commit()
