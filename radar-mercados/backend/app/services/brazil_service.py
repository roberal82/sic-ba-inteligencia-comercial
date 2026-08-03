"""Brasil: Banco Central do Brasil (API SGS, publica sin clave). Ibovespa/acciones sin API
oficial gratuita -> se documentan como pendientes y se sirven en modo demo."""
from app.core.config import get_settings
from app.core.logging import logger
from app.services import fallback_service
from app.services.base import SourceUnavailableError, build_indicator, fetch_json

settings = get_settings()

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados/ultimos/{n}"
# Series del SGS/BCB: 432=Selic meta, 433=IPCA variacion mensal, 1=USD/BRL venda (PTAX)
_SERIES = {
    "SELIC": (432, "Tasa Selic", "tasa", "%"),
    "IPCA": (433, "Inflacion IPCA (mensual)", "inflacion", "%"),
    "USDBRL": (1, "USD/BRL (PTAX)", "divisa", "BRL"),
}


async def _fetch_serie(serie: int, n: int = 2) -> list[dict]:
    url = BCB_SGS_URL.format(serie=serie, n=n)
    data = await fetch_json(url, params={"formato": "json"})
    if not isinstance(data, list) or not data:
        raise SourceUnavailableError(f"Serie BCB {serie} vacia o con formato inesperado")
    return data


async def get_indicators() -> list[dict]:
    demo_subset = [i for i in fallback_service.demo_indicators() if i["country"] == "brasil"]
    if settings.is_demo:
        return demo_subset

    live: list[dict] = []
    for symbol, (serie, name, category, unit) in _SERIES.items():
        try:
            rows = await _fetch_serie(serie, n=2)
            latest = rows[-1]
            previous = rows[-2] if len(rows) > 1 else None
            value = float(str(latest["valor"]).replace(",", "."))
            previous_value = float(str(previous["valor"]).replace(",", ".")) if previous else None
            live.append(
                build_indicator(
                    country="brasil",
                    market="BCB",
                    symbol=symbol,
                    name=name,
                    category=category,
                    value=round(value, 4),
                    previous_value=round(previous_value, 4) if previous_value is not None else None,
                    source="Banco Central do Brasil (SGS)",
                    source_url="https://api.bcb.gov.br/dados/serie/",
                    unit=unit if category != "divisa" else "",
                    currency="BRL" if category == "divisa" else "",
                    data_status="live",
                    confidence=0.9,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("brazil_service: fallo serie {} ({}): {}", serie, symbol, exc)
            fallback_item = next((i for i in demo_subset if i["symbol"] == symbol), None)
            if fallback_item:
                live.append({**fallback_item, "source": f"{fallback_item['source']} (BCB no disponible)"})

    # Ibovespa y acciones (Petrobras, Vale): sin API oficial gratuita -> demo documentado.
    pending_symbols = {"IBOV", "PETR4", "VALE3", "NTNB10"}
    live.extend(i for i in demo_subset if i["symbol"] in pending_symbols)
    return live
