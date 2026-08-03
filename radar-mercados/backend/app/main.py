"""Punto de entrada de la API Radar Regional de Mercados."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import (
    routes_analysis,
    routes_dashboard,
    routes_events,
    routes_health,
    routes_markets,
    routes_scenarios,
    routes_sources,
    routes_system,
)
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging, logger
from app.core.security import SecurityHeadersMiddleware, limiter
from app.jobs.scheduler import shutdown_scheduler, start_scheduler

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Iniciando {} v{} en modo {}", settings.app_name, settings.app_version, settings.app_mode)
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Aplicacion detenida")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API para el Radar Regional de Mercados: Paraguay, Brasil, Argentina, mercados "
        "globales, materias primas, divisas, criptomonedas y eventos geopoliticos "
        "georreferenciados, con analisis automatizado basado en reglas."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

api_router_prefix = "/api"
app.include_router(routes_health.router, prefix=api_router_prefix)
app.include_router(routes_dashboard.router, prefix=api_router_prefix)
app.include_router(routes_markets.router, prefix=api_router_prefix)
app.include_router(routes_events.router, prefix=api_router_prefix)
app.include_router(routes_analysis.router, prefix=api_router_prefix)
app.include_router(routes_scenarios.router, prefix=api_router_prefix)
app.include_router(routes_sources.router, prefix=api_router_prefix)
app.include_router(routes_system.router, prefix=api_router_prefix)
app.include_router(routes_system.admin_router, prefix=api_router_prefix)

# Sirve el frontend estatico directamente desde FastAPI para facilitar la ejecucion local
# (sin necesidad de Nginx). En despliegue con Docker, Nginx sirve /frontend y hace proxy a /api.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def serve_frontend() -> str:
        return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
