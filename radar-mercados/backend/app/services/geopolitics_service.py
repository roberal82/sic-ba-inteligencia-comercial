"""Eventos geopoliticos via GDELT Doc API (publica, sin clave). Los articulos se
transforman heuristicamente en eventos georreferenciados; ante cualquier fallo o
respuesta vacia se usa el conjunto demostrativo."""
import datetime as dt

from app.core.config import get_settings
from app.core.logging import logger
from app.services import fallback_service
from app.services.base import SourceUnavailableError, fetch_json

settings = get_settings()

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Consultas de vigilancia por region/tema. Se limita para no saturar la fuente.
_QUERIES = [
    ("brasil economia OR ibovespa OR selic", "Brasil", -14.2, -51.9, "macro"),
    ("paraguay economia OR agro OR hidrovia", "Paraguay", -23.4, -58.4, "macro"),
    ("argentina riesgo pais OR dolar OR reservas", "Argentina", -38.4, -63.6, "politico"),
    ("petroleo OR ormuz OR mar rojo", "Global", 20.0, 45.0, "conflicto"),
]
_HIGH_SEVERITY_KEYWORDS = ("guerra", "war", "ataque", "attack", "sanction", "sancion", "conflict", "conflicto")
_MEDIUM_SEVERITY_KEYWORDS = ("tension", "crisis", "riesgo", "risk", "alerta", "warning")


def _infer_severity(title: str) -> str:
    lowered = title.lower()
    if any(kw in lowered for kw in _HIGH_SEVERITY_KEYWORDS):
        return "high"
    if any(kw in lowered for kw in _MEDIUM_SEVERITY_KEYWORDS):
        return "medium"
    return "low"


async def _fetch_query(query: str, country: str, lat: float, lon: float, event_type: str) -> list[dict]:
    payload = await fetch_json(
        GDELT_URL,
        params={"query": query, "mode": "artlist", "maxrecords": 5, "format": "json", "sort": "hybridrel"},
    )
    articles = payload.get("articles", []) if isinstance(payload, dict) else []
    if not articles:
        raise SourceUnavailableError(f"GDELT sin articulos para consulta '{query}'")
    events = []
    for article in articles[:3]:
        title = article.get("title") or "Evento sin titulo"
        events.append(
            {
                "title": title,
                "summary": article.get("title", ""),
                "country": country,
                "region": country,
                "latitude": lat,
                "longitude": lon,
                "event_type": event_type,
                "severity": _infer_severity(title),
                "probability": 0.5,
                "source": "GDELT Doc API",
                "source_url": article.get("url", ""),
                "published_at": dt.datetime.now(dt.timezone.utc),
                "assets_affected": [],
                "sectors_affected": [],
                "expected_direction": "neutral",
                "time_horizon": "corto plazo",
                "confidence": 0.3,
            }
        )
    return events


async def get_events() -> list[dict]:
    if settings.is_demo:
        return fallback_service.demo_events()

    live: list[dict] = []
    for query, country, lat, lon, event_type in _QUERIES:
        try:
            live.extend(await _fetch_query(query, country, lat, lon, event_type))
        except Exception as exc:  # noqa: BLE001
            logger.warning("geopolitics_service: fallo GDELT para '{}': {}", query, exc)

    if not live:
        logger.warning("geopolitics_service: GDELT no disponible, usando eventos demo")
        return fallback_service.demo_events()
    return live
