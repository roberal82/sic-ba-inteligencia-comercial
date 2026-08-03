"""Mercados globales: indices, tasas y divisas via stooq.com (cotizaciones CSV publicas,
sin clave, con uso permitido para consulta no comercial). Si falla, cae a datos demo."""
import csv
import io

from app.core.config import get_settings
from app.core.logging import logger
from app.services import fallback_service
from app.services.base import SourceUnavailableError, build_indicator, fetch_text

settings = get_settings()

STOOQ_URL = "https://stooq.com/q/l/"
# symbol stooq -> (symbol interno, nombre, categoria, unidad, moneda)
_SYMBOLS = {
    "^spx": ("SPX", "S&P 500", "indice", "pts", ""),
    "^dji": ("DJI", "Dow Jones", "indice", "pts", ""),
    "^ndq": ("IXIC", "Nasdaq Composite", "indice", "pts", ""),
    "^vix": ("VIX", "Indice de volatilidad VIX", "volatilidad", "pts", ""),
    "eurusd": ("EURUSD", "EUR/USD", "divisa", "", "USD"),
}


async def _fetch_quotes(symbols: list[str]) -> dict[str, float]:
    csv_text = await fetch_text(
        STOOQ_URL, params={"s": ",".join(symbols), "f": "sd2t2ohlc", "e": "csv"}
    )
    reader = csv.DictReader(io.StringIO(csv_text))
    quotes: dict[str, float] = {}
    for row in reader:
        symbol = (row.get("Symbol") or "").lower()
        close = row.get("Close")
        if symbol and close not in (None, "", "N/D"):
            try:
                quotes[symbol] = float(close)
            except ValueError:
                continue
    if not quotes:
        raise SourceUnavailableError("stooq.com no devolvio cotizaciones validas")
    return quotes


async def get_indicators() -> list[dict]:
    demo_subset = [
        i
        for i in fallback_service.demo_indicators()
        if i["symbol"] in ("SPX", "DJI", "IXIC", "VIX", "EURUSD", "US10Y", "DXY", "EM")
    ]
    if settings.is_demo:
        return demo_subset

    live: list[dict] = []
    try:
        quotes = await _fetch_quotes(list(_SYMBOLS.keys()))
        for stooq_symbol, (symbol, name, category, unit, currency) in _SYMBOLS.items():
            if stooq_symbol not in quotes:
                continue
            live.append(
                build_indicator(
                    country="global",
                    market="stooq",
                    symbol=symbol,
                    name=name,
                    category=category,
                    value=quotes[stooq_symbol],
                    previous_value=None,
                    source="stooq.com",
                    source_url="https://stooq.com/",
                    unit=unit,
                    currency=currency,
                    data_status="live",
                    delayed_minutes=15,
                    confidence=0.7,
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("global_markets_service: fallo stooq, usando fallback demo: {}", exc)

    fetched_symbols = {item["symbol"] for item in live}
    live.extend(i for i in demo_subset if i["symbol"] not in fetched_symbols)
    # Treasury 10Y, DXY y MSCI EM no estan disponibles sin proveedor contratado (FRED/Twelve Data/Polygon).
    return live
