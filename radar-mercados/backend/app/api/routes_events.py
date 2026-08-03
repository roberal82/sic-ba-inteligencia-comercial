import datetime as dt

from fastapi import APIRouter

from app.services import geopolitics_service

router = APIRouter(prefix="/events", tags=["events"])


async def _filtered_events(
    country: str | None,
    severity: str | None,
    event_type: str | None,
    sector: str | None,
    asset: str | None,
    since_days: int | None,
) -> list[dict]:
    events = await geopolitics_service.get_events()
    if country:
        events = [e for e in events if e["country"].lower() == country.lower()]
    if severity:
        events = [e for e in events if e["severity"] == severity]
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    if sector:
        events = [e for e in events if any(sector.lower() in s.lower() for s in e.get("sectors_affected", []))]
    if asset:
        events = [e for e in events if any(asset.lower() in a.lower() for a in e.get("assets_affected", []))]
    if since_days:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=since_days)
        events = [e for e in events if e["published_at"] >= cutoff]
    return events


@router.get("")
async def list_events(
    country: str | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    sector: str | None = None,
    asset: str | None = None,
    since_days: int | None = None,
) -> list[dict]:
    return await _filtered_events(country, severity, event_type, sector, asset, since_days)


@router.get("/map")
async def events_map(
    country: str | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    sector: str | None = None,
    asset: str | None = None,
) -> list[dict]:
    """Version optimizada para el mapa: solo los campos necesarios para marcadores y popups."""
    events = await _filtered_events(country, severity, event_type, sector, asset, None)
    return [
        {
            "id": e.get("id", e["title"]),
            "title": e["title"],
            "summary": e["summary"],
            "country": e["country"],
            "region": e["region"],
            "latitude": e["latitude"],
            "longitude": e["longitude"],
            "event_type": e["event_type"],
            "severity": e["severity"],
            "probability": e["probability"],
            "assets_affected": e.get("assets_affected", []),
            "sectors_affected": e.get("sectors_affected", []),
            "expected_direction": e.get("expected_direction", "neutral"),
            "confidence": e.get("confidence", 0.5),
            "source": e["source"],
            "source_url": e.get("source_url", ""),
            "published_at": e["published_at"],
        }
        for e in events
    ]
