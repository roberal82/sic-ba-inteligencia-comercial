import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import MarketIndicator
from app.repositories.market_repository import fetch_all_indicators

router = APIRouter(prefix="/markets", tags=["markets"])

VALID_COUNTRIES = {"brasil", "paraguay", "argentina", "global"}


@router.get("")
async def list_markets(country: str | None = None, category: str | None = None) -> list[dict]:
    indicators = await fetch_all_indicators()
    if country:
        indicators = [i for i in indicators if i["country"] == country]
    if category:
        indicators = [i for i in indicators if i["category"] == category]
    return indicators


@router.get("/{country}")
async def markets_by_country(country: str) -> list[dict]:
    if country not in VALID_COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Pais desconocido: {country}")
    indicators = await fetch_all_indicators()
    return [i for i in indicators if i["country"] == country]


@router.get("/{country}/{category}")
async def markets_by_country_category(country: str, category: str) -> list[dict]:
    if country not in VALID_COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Pais desconocido: {country}")
    indicators = await fetch_all_indicators()
    filtered = [i for i in indicators if i["country"] == country and i["category"] == category]
    return filtered


@router.get("/history/{symbol}")
def market_history(symbol: str, period_days: int = 30, db: Session = Depends(get_db)) -> dict:
    """Historial real acumulado por los jobs programados. Si aun no hay suficientes puntos
    (por ejemplo, en una instalacion recien iniciada), se informa explicitamente en vez de
    inventar una serie temporal."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=period_days)
    stmt = (
        select(MarketIndicator)
        .where(MarketIndicator.symbol == symbol, MarketIndicator.timestamp >= cutoff)
        .order_by(MarketIndicator.timestamp.asc())
    )
    rows = db.execute(stmt).scalars().all()
    points = [{"timestamp": row.timestamp, "value": row.value, "source": row.source} for row in rows]
    return {
        "symbol": symbol,
        "period_days": period_days,
        "points": points,
        "sufficient_history": len(points) >= 2,
        "note": (
            "Historial insuficiente: se acumula automaticamente con cada ejecucion de las "
            "tareas programadas. Ninguna cifra fue inventada."
            if len(points) < 2
            else ""
        ),
    }
