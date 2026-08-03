import datetime as dt

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": settings.app_mode,
        "time": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
