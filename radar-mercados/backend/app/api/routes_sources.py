import datetime as dt

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/sources", tags=["sources"])
settings = get_settings()


def _status_list() -> list[dict]:
    now = dt.datetime.now(dt.timezone.utc)
    demo = settings.is_demo
    live_status = "no_disponible" if demo else "operativo"
    return [
        {
            "name": "Banco Central do Brasil (SGS)", "country": "brasil", "category": "macro/tasas/fx",
            "status": live_status, "last_success": None if demo else now,
            "notes": "API publica sin clave (Selic, IPCA, USD/BRL). Ibovespa y acciones sin API oficial gratuita.",
        },
        {
            "name": "BCRA (API estadisticas v3.0)", "country": "argentina", "category": "reservas/fx",
            "status": live_status, "last_success": None if demo else now,
            "notes": "API publica sin clave. Merval, riesgo pais, MEP/CCL y bonos requieren proveedor de terceros.",
        },
        {
            "name": "Banco Central del Paraguay / BVPASA", "country": "paraguay", "category": "macro/bolsa",
            "status": "pendiente_credenciales", "last_success": None,
            "notes": "Sin API JSON publica documentada al momento de esta version. Se sirven datos demostrativos.",
        },
        {
            "name": "stooq.com", "country": "global", "category": "indices/fx/commodities",
            "status": live_status, "last_success": None if demo else now,
            "notes": "Cotizaciones con retardo (~15 min) sin clave. Usado como respaldo, se documenta la fuente.",
        },
        {
            "name": "CoinGecko", "country": "global", "category": "cripto",
            "status": live_status, "last_success": None if demo else now,
            "notes": "API publica sin clave para BTC y ETH.",
        },
        {
            "name": "GDELT Doc API", "country": "global", "category": "geopolitica",
            "status": live_status, "last_success": None if demo else now,
            "notes": "API publica sin clave. Los eventos se derivan heuristicamente de titulares.",
        },
        {
            "name": "Alpha Vantage", "country": "global", "category": "mercados",
            "status": "operativo" if settings.alpha_vantage_api_key else "pendiente_credenciales",
            "last_success": None,
            "notes": "Requiere ALPHA_VANTAGE_API_KEY en .env. No configurada por defecto.",
        },
        {
            "name": "Twelve Data", "country": "global", "category": "mercados",
            "status": "operativo" if settings.twelve_data_api_key else "pendiente_credenciales",
            "last_success": None,
            "notes": "Requiere TWELVE_DATA_API_KEY en .env. No configurada por defecto.",
        },
        {
            "name": "Polygon.io", "country": "global", "category": "mercados",
            "status": "operativo" if settings.polygon_api_key else "pendiente_credenciales",
            "last_success": None,
            "notes": "Requiere POLYGON_API_KEY en .env. No configurada por defecto.",
        },
        {
            "name": "BYMA / CNV / INDEC", "country": "argentina", "category": "bolsa/riesgo pais",
            "status": "pendiente_credenciales", "last_success": None,
            "notes": "Sin API publica gratuita identificada. Requiere convenio o proveedor de datos de mercado.",
        },
    ]


@router.get("")
def list_sources() -> list[dict]:
    return _status_list()
