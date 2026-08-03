"""Argentina: BCRA expone una API publica (estadisticas cambiarias y monetarias) sin clave.
Merval, riesgo pais, MEP/CCL y bonos no tienen API oficial gratuita -> se documentan como
pendientes y se sirven con datos demo hasta contratar un proveedor (ej. Twelve Data, Polygon)."""
from app.core.config import get_settings
from app.core.logging import logger
from app.services import fallback_service
from app.services.base import SourceUnavailableError, build_indicator, fetch_json

settings = get_settings()

BCRA_MONETARIAS_URL = "https://api.bcra.gob.ar/estadisticas/v3.0/monetarias"
# idVariable de referencia BCRA: 1=Reservas internacionales (USD mill), 6=Tipo de cambio mayorista A3500
_VARIABLES = {
    "RESERVAS": (1, "Reservas BCRA", "reservas", "USD mill"),
    "USDARS_OFICIAL": (6, "Dolar mayorista (A3500)", "divisa", "ARS"),
}


async def get_indicators() -> list[dict]:
    demo_subset = [i for i in fallback_service.demo_indicators() if i["country"] == "argentina"]
    if settings.is_demo:
        return demo_subset

    live: list[dict] = []
    try:
        payload = await fetch_json(BCRA_MONETARIAS_URL)
        results = payload.get("results", []) if isinstance(payload, dict) else []
        by_id = {item.get("idVariable"): item for item in results}
        for symbol, (var_id, name, category, unit) in _VARIABLES.items():
            item = by_id.get(var_id)
            if not item or "valor" not in item:
                raise SourceUnavailableError(f"BCRA no devolvio idVariable={var_id}")
            value = float(item["valor"])
            live.append(
                build_indicator(
                    country="argentina",
                    market="BCRA",
                    symbol=symbol,
                    name=name,
                    category=category,
                    value=round(value, 4),
                    previous_value=None,
                    source="BCRA (API estadisticas v3.0)",
                    source_url="https://api.bcra.gob.ar/estadisticas/v3.0/monetarias",
                    unit=unit if category != "divisa" else "",
                    currency="ARS" if category == "divisa" else "",
                    data_status="live",
                    confidence=0.85,
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("argentina_service: fallo BCRA, usando fallback demo: {}", exc)
        live = [
            {**i, "source": f"{i['source']} (BCRA no disponible)"}
            for i in demo_subset
            if i["symbol"] in _VARIABLES
        ]

    pending_symbols = {"MERV", "RIESGO_PAIS", "USDARS_MEP", "USDARS_CCL", "TASA_REF", "INFLACION"}
    live.extend(i for i in demo_subset if i["symbol"] in pending_symbols)
    return live
