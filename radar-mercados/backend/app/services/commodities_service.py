"""Materias primas via stooq.com (mismo mecanismo que global_markets_service)."""
import csv
import io

from app.core.config import get_settings
from app.core.logging import logger
from app.services import fallback_service
from app.services.base import SourceUnavailableError, build_indicator, fetch_text

settings = get_settings()

STOOQ_URL = "https://stooq.com/q/l/"
_SYMBOLS = {
    "xauusd": ("GOLD", "Oro", "USD/oz"),
    "xagusd": ("SILVER", "Plata", "USD/oz"),
    "cl.f": ("WTI", "Petroleo WTI", "USD/bbl"),
    "hg.f": ("COPPER", "Cobre", "USD/lb"),
}


async def get_indicators() -> list[dict]:
    demo_subset = [
        i
        for i in fallback_service.demo_indicators()
        if i["symbol"] in ("GOLD", "SILVER", "WTI", "BRENT", "COPPER", "SOYBEAN")
    ]
    if settings.is_demo:
        return demo_subset

    live: list[dict] = []
    try:
        csv_text = await fetch_text(
            STOOQ_URL, params={"s": ",".join(_SYMBOLS.keys()), "f": "sd2t2ohlc", "e": "csv"}
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
            raise SourceUnavailableError("stooq.com no devolvio cotizaciones de commodities validas")
        for stooq_symbol, (symbol, name, unit) in _SYMBOLS.items():
            if stooq_symbol not in quotes:
                continue
            live.append(
                build_indicator(
                    country="global",
                    market="stooq",
                    symbol=symbol,
                    name=name,
                    category="commodity",
                    value=quotes[stooq_symbol],
                    previous_value=None,
                    source="stooq.com",
                    source_url="https://stooq.com/",
                    unit=unit,
                    data_status="live",
                    delayed_minutes=15,
                    confidence=0.7,
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("commodities_service: fallo stooq, usando fallback demo: {}", exc)

    fetched_symbols = {item["symbol"] for item in live}
    live.extend(i for i in demo_subset if i["symbol"] not in fetched_symbols)
    # Brent y soja Chicago sin ticker confiable sin clave -> quedan como demo hasta contratar proveedor.
    return live
