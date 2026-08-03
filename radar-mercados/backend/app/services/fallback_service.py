"""Datos de respaldo (demostrativos) usados cuando una fuente en vivo falla o en APP_MODE=demo.

IMPORTANTE: estos valores son ilustrativos, basados en ordenes de magnitud publicos y
razonables al momento de escribir este modulo. NO son cotizaciones en vivo. Cada registro
generado a partir de aqui se marca explicitamente con data_status="demo" para que el
frontend y la API nunca los presenten como datos reales.
"""
import datetime as dt
from typing import Any

DEMO_SOURCE_NOTE = "Dato demostrativo (fallback) - no es cotizacion en vivo"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _indicator(
    country: str,
    market: str,
    symbol: str,
    name: str,
    category: str,
    value: float,
    previous_value: float,
    unit: str = "",
    currency: str = "",
) -> dict[str, Any]:
    change = round(value - previous_value, 6)
    change_percent = round((change / previous_value) * 100, 4) if previous_value else 0.0
    return {
        "country": country,
        "market": market,
        "symbol": symbol,
        "name": name,
        "category": category,
        "value": value,
        "unit": unit,
        "currency": currency,
        "previous_value": previous_value,
        "change": change,
        "change_percent": change_percent,
        "timestamp": _now(),
        "source": DEMO_SOURCE_NOTE,
        "source_url": "",
        "data_status": "demo",
        "delayed_minutes": 0,
        "confidence": 0.3,
    }


def demo_indicators() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [
        # --- Brasil ---
        _indicator("brasil", "B3", "IBOV", "Ibovespa", "indice", 127850, 127040, "pts"),
        _indicator("brasil", "FX", "USDBRL", "USD/BRL", "divisa", 5.077, 5.066, currency="BRL"),
        _indicator("brasil", "BCB", "SELIC", "Tasa Selic", "tasa", 10.50, 10.50, "%"),
        _indicator("brasil", "IBGE", "IPCA", "Inflacion IPCA (12m)", "inflacion", 4.20, 4.30, "%"),
        _indicator("brasil", "B3", "PETR4", "Petrobras PN", "accion", 38.20, 37.85, "BRL", "BRL"),
        _indicator("brasil", "B3", "VALE3", "Vale ON", "accion", 61.40, 62.10, "BRL", "BRL"),
        _indicator("brasil", "Tesouro", "NTNB10", "Bono soberano 10a (real)", "bono", 6.10, 6.05, "%"),
        # --- Paraguay ---
        _indicator("paraguay", "BCP", "USDPYG", "USD/PYG", "divisa", 7650, 7644, currency="PYG"),
        _indicator("paraguay", "BCP", "TPM", "Tasa de politica monetaria", "tasa", 6.00, 6.00, "%"),
        _indicator("paraguay", "BCP", "IPC", "Inflacion interanual", "inflacion", 3.80, 3.90, "%"),
        _indicator("paraguay", "BCP", "RIN", "Reservas internacionales", "reservas", 11200, 11150, "USD mill"),
        _indicator("paraguay", "BVPASA", "IBVPASA", "Indice BVPASA", "indice", 1102, 1100, "pts"),
        _indicator("paraguay", "Commodities", "SOJA_PY", "Soja (referencia exportacion)", "commodity", 405, 410, "USD/ton"),
        # --- Argentina ---
        _indicator("argentina", "BYMA", "MERV", "S&P Merval", "indice", 1488450, 1494440, "pts"),
        _indicator("argentina", "BCRA", "RIESGO_PAIS", "Riesgo pais (EMBI+ AR)", "riesgo_pais", 430, 428, "pb"),
        _indicator("argentina", "BCRA", "USDARS_OFICIAL", "Dolar oficial", "divisa", 1050, 1048, currency="ARS"),
        _indicator("argentina", "BCRA", "USDARS_MEP", "Dolar MEP", "divisa", 1516, 1508, currency="ARS"),
        _indicator("argentina", "BCRA", "USDARS_CCL", "Contado con liquidacion", "divisa", 1532, 1520, currency="ARS"),
        _indicator("argentina", "BCRA", "RESERVAS", "Reservas BCRA", "reservas", 29500, 29300, "USD mill"),
        _indicator("argentina", "BCRA", "TASA_REF", "Tasa de referencia (LEFI)", "tasa", 29.00, 29.00, "%"),
        _indicator("argentina", "INDEC", "INFLACION", "Inflacion mensual", "inflacion", 2.10, 2.40, "%"),
        # --- Global ---
        _indicator("global", "NYSE", "SPX", "S&P 500", "indice", 5610, 5578, "pts"),
        _indicator("global", "NASDAQ", "IXIC", "Nasdaq Composite", "indice", 17900, 17750, "pts"),
        _indicator("global", "NYSE", "DJI", "Dow Jones", "indice", 41200, 41050, "pts"),
        _indicator("global", "UST", "US10Y", "Treasury 10Y", "tasa", 4.35, 4.30, "%"),
        _indicator("global", "ICE", "DXY", "Indice dolar (DXY)", "divisa", 103.4, 103.1, "pts"),
        _indicator("global", "FX", "EURUSD", "EUR/USD", "divisa", 1.085, 1.082, currency="USD"),
        _indicator("global", "CBOE", "VIX", "Indice de volatilidad VIX", "volatilidad", 14.8, 15.3, "pts"),
        _indicator("global", "MSCI", "EM", "MSCI Emerging Markets", "indice", 1120, 1112, "pts"),
        # --- Commodities ---
        _indicator("global", "COMEX", "GOLD", "Oro", "commodity", 4108, 4071, "USD/oz"),
        _indicator("global", "COMEX", "SILVER", "Plata", "commodity", 48.2, 47.6, "USD/oz"),
        _indicator("global", "NYMEX", "WTI", "Petroleo WTI", "commodity", 78.4, 76.9, "USD/bbl"),
        _indicator("global", "ICE", "BRENT", "Petroleo Brent", "commodity", 82.1, 80.5, "USD/bbl"),
        _indicator("global", "COMEX", "COPPER", "Cobre", "commodity", 4.55, 4.49, "USD/lb"),
        _indicator("global", "CBOT", "SOYBEAN", "Soja (Chicago)", "commodity", 1042, 1038, "USd/bu"),
        # --- Cripto ---
        _indicator("global", "Cripto", "BTC", "Bitcoin", "cripto", 98500, 96200, "USD"),
        _indicator("global", "Cripto", "ETH", "Ethereum", "cripto", 3650, 3580, "USD"),
    ]
    return items


def demo_events() -> list[dict[str, Any]]:
    now = _now()
    raw = [
        dict(
            title="Riesgo logistico en el Estrecho de Ormuz",
            summary="Tensiones que podrian afectar el transito de petroleo y el costo de fletes maritimos.",
            country="Iran", region="Golfo Persico", latitude=26.57, longitude=56.25,
            event_type="conflicto", severity="high", probability=0.4,
            assets_affected=["Brent", "WTI", "Oro"], sectors_affected=["Energia", "Transporte"],
            expected_direction="up", time_horizon="corto plazo", confidence=0.4,
        ),
        dict(
            title="Tension en rutas del Mar Rojo",
            summary="Ataques a embarcaciones comerciales elevan primas de seguro y desvian rutas navieras.",
            country="Yemen", region="Mar Rojo", latitude=15.55, longitude=42.55,
            event_type="conflicto", severity="high", probability=0.45,
            assets_affected=["Navieras", "Brent"], sectors_affected=["Transporte", "Energia"],
            expected_direction="up", time_horizon="corto plazo", confidence=0.45,
        ),
        dict(
            title="Flujo de capital extranjero hacia Brasil",
            summary="Entrada neta de inversion de cartera hacia renta variable brasileña.",
            country="Brasil", region="Sao Paulo", latitude=-23.55, longitude=-46.63,
            event_type="mercado", severity="medium", probability=0.5,
            assets_affected=["Ibovespa", "BRL"], sectors_affected=["Financiero"],
            expected_direction="up", time_horizon="medio plazo", confidence=0.5,
        ),
        dict(
            title="Cosecha y exportaciones de soja",
            summary="Volumen de exportacion agricola con impacto directo en divisas y actividad economica.",
            country="Paraguay", region="Region Oriental", latitude=-25.30, longitude=-57.64,
            event_type="agro", severity="medium", probability=0.55,
            assets_affected=["PYG", "Soja"], sectors_affected=["Agro", "Logistica"],
            expected_direction="neutral", time_horizon="medio plazo", confidence=0.4,
        ),
        dict(
            title="Nivel del rio Paraguay e hidrovia",
            summary="Bajante o crecida del rio afecta el transporte fluvial de granos y combustibles.",
            country="Paraguay", region="Hidrovia Paraguay-Parana", latitude=-27.33, longitude=-58.66,
            event_type="logistica", severity="medium", probability=0.35,
            assets_affected=["Agro", "Combustibles"], sectors_affected=["Logistica", "Agro"],
            expected_direction="neutral", time_horizon="corto plazo", confidence=0.35,
        ),
        dict(
            title="Riesgo pais y brecha cambiaria",
            summary="Evolucion del riesgo pais y del dolar financiero condicionan el apetito por activos argentinos.",
            country="Argentina", region="Buenos Aires", latitude=-34.60, longitude=-58.38,
            event_type="politico", severity="high", probability=0.5,
            assets_affected=["Bonos AR", "Merval", "ARS"], sectors_affected=["Financiero"],
            expected_direction="neutral", time_horizon="corto plazo", confidence=0.4,
        ),
        dict(
            title="Demanda china de materias primas",
            summary="Señales de actividad industrial en China con impacto en metales y agro regional.",
            country="China", region="Beijing", latitude=39.90, longitude=116.40,
            event_type="macro", severity="medium", probability=0.5,
            assets_affected=["Cobre", "Hierro", "Soja"], sectors_affected=["Mineria", "Agro"],
            expected_direction="up", time_horizon="medio plazo", confidence=0.4,
        ),
        dict(
            title="Decision de tasas de la Reserva Federal",
            summary="Reunion de politica monetaria de EE.UU. con impacto en tasas largas y dolar global.",
            country="Estados Unidos", region="Washington D.C.", latitude=38.90, longitude=-77.04,
            event_type="banco_central", severity="high", probability=0.6,
            assets_affected=["Treasury 10Y", "DXY", "Oro"], sectors_affected=["Financiero", "Tecnologia"],
            expected_direction="neutral", time_horizon="corto plazo", confidence=0.5,
        ),
    ]
    events = []
    for idx, item in enumerate(raw):
        events.append(
            {
                **item,
                "published_at": now - dt.timedelta(hours=idx * 3),
                "source": DEMO_SOURCE_NOTE,
                "source_url": "",
            }
        )
    return events


def demo_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "profile": "conservador",
            "liquidity": 35, "fixed_income": 35, "gold": 10, "global_equities": 15,
            "brazil": 3, "paraguay": 2, "argentina": 0, "commodities": 0, "crypto": 0,
            "risk_level": "bajo",
            "explanation": (
                "Perfil orientado a preservacion de capital: alta liquidez, bonos de "
                "alta calidad crediticia, baja exposicion regional, oro moderado como "
                "cobertura y sin apalancamiento."
            ),
        },
        {
            "profile": "moderado",
            "liquidity": 15, "fixed_income": 25, "gold": 10, "global_equities": 25,
            "brazil": 12, "paraguay": 8, "argentina": 3, "commodities": 2, "crypto": 0,
            "risk_level": "medio",
            "explanation": (
                "Diversificacion global con renta fija de base, exposicion relevante a "
                "Brasil y Paraguay, oro como cobertura y exposicion tactica limitada a "
                "Argentina."
            ),
        },
        {
            "profile": "agresivo",
            "liquidity": 5, "fixed_income": 10, "gold": 8, "global_equities": 30,
            "brazil": 15, "paraguay": 5, "argentina": 15, "commodities": 7, "crypto": 5,
            "risk_level": "alto",
            "explanation": (
                "Mayor ponderacion en renta variable, energia, tecnologia y mercados "
                "emergentes, con exposicion tactica a Argentina y cripto limitada. "
                "Requiere control estricto de perdidas."
            ),
        },
    ]
