from fastapi import APIRouter

from app.repositories.market_repository import fetch_all_indicators
from app.services import analysis_service, geopolitics_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("")
async def list_analysis(scope: str | None = None) -> list[dict]:
    indicators = await fetch_all_indicators()
    events = await geopolitics_service.get_events()
    results = analysis_service.run_all(indicators, events)
    if scope:
        results = [r for r in results if r["scope"] == scope]
    return results
