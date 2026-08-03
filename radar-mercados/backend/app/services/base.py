"""Utilidades comunes para servicios de integracion: cliente HTTP con timeout/reintentos."""
import asyncio
import datetime as dt
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class SourceUnavailableError(Exception):
    """Se lanza cuando una fuente externa no responde tras los reintentos configurados."""


def build_indicator(
    *,
    country: str,
    market: str,
    symbol: str,
    name: str,
    category: str,
    value: float,
    previous_value: float | None,
    source: str,
    source_url: str = "",
    unit: str = "",
    currency: str = "",
    data_status: str = "live",
    delayed_minutes: int = 0,
    confidence: float = 0.8,
) -> dict[str, Any]:
    """Construye un registro de indicador con la misma forma que los datos demostrativos."""
    change = round(value - previous_value, 6) if previous_value is not None else None
    change_percent = (
        round((change / previous_value) * 100, 4) if previous_value else None
    )
    return {
        "country": country,
        "market": market,
        "symbol": symbol,
        "name": name,
        "category": category,
        "value": value,
        "unit": unit,
        "currency": currency,
        "previous_value": previous_value,
        "change": change,
        "change_percent": change_percent,
        "timestamp": dt.datetime.now(dt.timezone.utc),
        "source": source,
        "source_url": source_url,
        "data_status": data_status,
        "delayed_minutes": delayed_minutes,
        "confidence": confidence,
    }


async def fetch_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """Hace GET con timeout y reintentos con backoff exponencial. Lanza SourceUnavailableError si falla."""
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        for attempt in range(settings.http_max_retries + 1):
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Intento {}/{} fallido para {}: {}",
                    attempt + 1,
                    settings.http_max_retries + 1,
                    url,
                    exc,
                )
                if attempt < settings.http_max_retries:
                    await asyncio.sleep(2**attempt * 0.5)
    raise SourceUnavailableError(f"No se pudo obtener {url}: {last_error}")


async def fetch_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        for attempt in range(settings.http_max_retries + 1):
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.text
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Intento {}/{} fallido para {}: {}",
                    attempt + 1,
                    settings.http_max_retries + 1,
                    url,
                    exc,
                )
                if attempt < settings.http_max_retries:
                    await asyncio.sleep(2**attempt * 0.5)
    raise SourceUnavailableError(f"No se pudo obtener {url}: {last_error}")
