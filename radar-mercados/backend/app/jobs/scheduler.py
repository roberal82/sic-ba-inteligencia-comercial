"""Tareas programadas: mercados, macro, noticias/eventos, analisis, limpieza y backup.

Usa APScheduler (AsyncIOScheduler) embebido en el proceso de FastAPI. Cada job registra
su ultima ejecucion, duracion y estado para exponerlos en /api/system/status.
"""
import datetime as dt
import shutil
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.cache import cache_clear
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import logger
from app.repositories.market_repository import fetch_all_indicators, persist_indicators
from app.services import geopolitics_service

settings = get_settings()
scheduler = AsyncIOScheduler()

_job_state: dict[str, dict[str, Any]] = {}


def _record(job_id: str, *, started_at: dt.datetime, error: str | None) -> None:
    finished_at = dt.datetime.now(dt.timezone.utc)
    _job_state[job_id] = {
        "job_id": job_id,
        "last_run": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "status": "error" if error else "ok",
        "error": error,
    }


async def job_refresh_markets() -> None:
    started = dt.datetime.now(dt.timezone.utc)
    error = None
    try:
        indicators = await fetch_all_indicators(use_cache=False)
        with SessionLocal() as db:
            persist_indicators(db, indicators)
        logger.info("job_refresh_markets: {} indicadores actualizados", len(indicators))
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        logger.error("job_refresh_markets fallo: {}", exc)
    _record("refresh_markets", started_at=started, error=error)


async def job_refresh_events() -> None:
    started = dt.datetime.now(dt.timezone.utc)
    error = None
    try:
        events = await geopolitics_service.get_events()
        logger.info("job_refresh_events: {} eventos actualizados", len(events))
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        logger.error("job_refresh_events fallo: {}", exc)
    _record("refresh_events", started_at=started, error=error)


async def job_cleanup() -> None:
    """Elimina indicadores historicos con mas de 90 dias para no crecer indefinidamente."""
    started = dt.datetime.now(dt.timezone.utc)
    error = None
    try:
        from app.models.models import MarketIndicator

        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)
        with SessionLocal() as db:
            deleted = db.query(MarketIndicator).filter(MarketIndicator.timestamp < cutoff).delete()
            db.commit()
        logger.info("job_cleanup: {} registros antiguos eliminados", deleted)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        logger.error("job_cleanup fallo: {}", exc)
    _record("cleanup", started_at=started, error=error)


async def job_backup() -> None:
    """Copia el archivo SQLite (si aplica) a un directorio de backups con marca de tiempo."""
    started = dt.datetime.now(dt.timezone.utc)
    error = None
    try:
        if settings.database_url.startswith("sqlite"):
            db_path = Path(settings.database_url.split("///")[-1])
            if db_path.exists():
                backup_dir = Path("backups")
                backup_dir.mkdir(exist_ok=True)
                stamp = started.strftime("%Y%m%d_%H%M%S")
                shutil.copy2(db_path, backup_dir / f"{db_path.stem}_{stamp}.db")
                logger.info("job_backup: respaldo creado para {}", db_path)
        else:
            logger.info("job_backup: motor no-SQLite, el respaldo debe gestionarse a nivel de infraestructura")
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        logger.error("job_backup fallo: {}", exc)
    _record("backup", started_at=started, error=error)


def start_scheduler() -> None:
    if not settings.enable_scheduler:
        logger.info("Scheduler deshabilitado por configuracion (ENABLE_SCHEDULER=false)")
        return
    if scheduler.running:
        return

    scheduler.add_job(
        job_refresh_markets, IntervalTrigger(minutes=settings.refresh_minutes_markets),
        id="refresh_markets", replace_existing=True,
    )
    scheduler.add_job(
        job_refresh_events, IntervalTrigger(minutes=settings.refresh_minutes_events),
        id="refresh_events", replace_existing=True,
    )
    scheduler.add_job(
        lambda: cache_clear(), IntervalTrigger(minutes=settings.refresh_minutes_macro),
        id="cache_reset_macro", replace_existing=True,
    )
    scheduler.add_job(job_cleanup, IntervalTrigger(hours=24), id="cleanup", replace_existing=True)
    scheduler.add_job(job_backup, IntervalTrigger(hours=24), id="backup", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler iniciado: mercados cada {} min, eventos cada {} min", settings.refresh_minutes_markets, settings.refresh_minutes_events)


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def get_job_status() -> list[dict]:
    jobs = []
    for job in scheduler.get_jobs():
        state = _job_state.get(job.id, {})
        jobs.append(
            {
                "job_id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "last_run": state.get("last_run"),
                "duration_seconds": state.get("duration_seconds"),
                "status": state.get("status", "pendiente"),
                "error": state.get("error"),
            }
        )
    return jobs
