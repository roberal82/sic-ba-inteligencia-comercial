import datetime as dt

from fastapi import APIRouter

from app.api.routes_sources import _status_list
from app.core.config import get_settings
from app.repositories.market_repository import fetch_all_indicators
from app.services import analysis_service, geopolitics_service

router = APIRouter(tags=["dashboard"])
settings = get_settings()

KPI_SYMBOLS = [
    "IBOV", "IBVPASA", "MERV", "USDBRL", "USDPYG", "USDARS_OFICIAL",
    "RIESGO_PAIS", "SELIC", "TPM", "GOLD", "BRENT", "BTC", "VIX", "US10Y",
]


@router.get("/dashboard")
async def dashboard(country: str = "regional", period_days: int = 7) -> dict:
    indicators = await fetch_all_indicators()
    events = await geopolitics_service.get_events()
    analysis = analysis_service.run_all(indicators, events)

    filtered_indicators = indicators if country == "regional" else [i for i in indicators if i["country"] == country]
    kpis = [i for i in indicators if i["symbol"] in KPI_SYMBOLS]

    return {
        "mode": settings.app_mode,
        "generated_at": dt.datetime.now(dt.timezone.utc),
        "country": country,
        "period_days": period_days,
        "kpis": kpis,
        "indicators": filtered_indicators,
        "events": events,
        "analysis": analysis,
        "sources": _status_list(),
    }
