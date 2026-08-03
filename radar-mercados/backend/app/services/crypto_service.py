"""Criptomonedas via CoinGecko (API publica, sin clave). Fallback a datos demo si falla."""
from app.core.config import get_settings
from app.core.logging import logger
from app.services import fallback_service
from app.services.base import SourceUnavailableError, build_indicator, fetch_json

settings = get_settings()

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
_COINS = {"bitcoin": ("BTC", "Bitcoin"), "ethereum": ("ETH", "Ethereum")}


async def get_indicators() -> list[dict]:
    if settings.is_demo:
        return [i for i in fallback_service.demo_indicators() if i["symbol"] in ("BTC", "ETH")]

    try:
        data = await fetch_json(
            COINGECKO_URL,
            params={
                "ids": ",".join(_COINS.keys()),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
        )
        indicators = []
        for coin_id, (symbol, name) in _COINS.items():
            entry = data.get(coin_id)
            if not entry or "usd" not in entry:
                raise SourceUnavailableError(f"CoinGecko no devolvio precio para {coin_id}")
            price = float(entry["usd"])
            change_pct = float(entry.get("usd_24h_change", 0.0))
            previous = price / (1 + change_pct / 100) if change_pct != -100 else None
            indicators.append(
                build_indicator(
                    country="global",
                    market="Cripto",
                    symbol=symbol,
                    name=name,
                    category="cripto",
                    value=round(price, 2),
                    previous_value=round(previous, 2) if previous else None,
                    source="CoinGecko",
                    source_url="https://www.coingecko.com/",
                    currency="USD",
                    data_status="live",
                    confidence=0.9,
                )
            )
        return indicators
    except Exception as exc:  # noqa: BLE001
        logger.warning("crypto_service: fallo CoinGecko, usando fallback demo: {}", exc)
        return [
            {**i, "source": f"{i['source']} (CoinGecko no disponible)"}
            for i in fallback_service.demo_indicators()
            if i["symbol"] in ("BTC", "ETH")
        ]
