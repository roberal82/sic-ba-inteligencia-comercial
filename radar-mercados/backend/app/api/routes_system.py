import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.cache import cache_backend_name, cache_clear
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import verify_admin_token
from app.jobs.scheduler import get_job_status
from app.repositories.market_repository import fetch_all_indicators

router = APIRouter(prefix="/system", tags=["system"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


@router.get("/status")
def system_status() -> dict:
    database_ok = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database_ok = False

    return {
        "app_mode": settings.app_mode,
        "app_version": settings.app_version,
        "server_time": dt.datetime.now(dt.timezone.utc),
        "database_ok": database_ok,
        "cache_backend": cache_backend_name(),
        "scheduler_enabled": settings.enable_scheduler,
        "jobs": get_job_status(),
    }


@admin_router.post("/refresh")
async def admin_refresh(_: None = Depends(verify_admin_token)) -> dict:
    """Fuerza una actualizacion inmediata de indicadores, ignorando la cache."""
    cache_clear()
    indicators = await fetch_all_indicators(use_cache=False)
    return {
        "refreshed_at": dt.datetime.now(dt.timezone.utc),
        "indicators_count": len(indicators),
    }
