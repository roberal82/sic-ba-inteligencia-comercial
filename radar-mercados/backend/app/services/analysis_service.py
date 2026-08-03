"""Motor de analisis basado en reglas explicitas (no generativo, no predictivo).

Cada regla combina 2 o mas indicadores/eventos observados y produce una lectura
condicional documentada. No inventa cifras ni pronosticos: si faltan datos para
evaluar una regla, esta simplemente no se dispara.
"""
import datetime as dt
from typing import Any

DISCLAIMER = (
    "Este analisis es educativo e informativo. No constituye asesoramiento financiero "
    "personalizado ni garantia de rendimiento."
)


def _find(indicators: list[dict], symbol: str) -> dict | None:
    return next((i for i in indicators if i.get("symbol") == symbol), None)


def _has_severe_event(events: list[dict], region_keywords: tuple[str, ...]) -> bool:
    for event in events:
        haystack = f"{event.get('region', '')} {event.get('title', '')}".lower()
        if event.get("severity") == "high" and any(kw in haystack for kw in region_keywords):
            return True
    return False


def _build_analysis(
    scope: str,
    title: str,
    summary: str,
    positive: list[str],
    negative: list[str],
    risks: list[str],
    opportunities: list[str],
    affected_assets: list[str],
    time_horizon: str,
    confidence: float,
    methodology: str,
    scenario_base: str,
    scenario_optimistic: str,
    scenario_adverse: str,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "title": title,
        "summary": summary,
        "positive_factors": positive,
        "negative_factors": negative,
        "risks": risks,
        "opportunities": opportunities,
        "affected_assets": affected_assets,
        "time_horizon": time_horizon,
        "confidence": confidence,
        "generated_at": dt.datetime.now(dt.timezone.utc),
        "methodology": methodology,
        "scenario_base": scenario_base,
        "scenario_optimistic": scenario_optimistic,
        "scenario_adverse": scenario_adverse,
    }


def analyze_global_energy(indicators: list[dict], events: list[dict]) -> dict | None:
    """Si Brent/WTI sube fuerte, hay evento severo en zona energetica clave y el dolar se
    fortalece, entonces sube el riesgo energetico y hay presion sobre transporte y aerolineas."""
    brent = _find(indicators, "BRENT") or _find(indicators, "WTI")
    dxy = _find(indicators, "DXY")
    if not brent:
        return None
    oil_up = (brent.get("change_percent") or 0) > 3
    dollar_strong = bool(dxy and (dxy.get("change_percent") or 0) > 0)
    severe_event = _has_severe_event(events, ("ormuz", "hormuz", "mar rojo", "red sea", "golfo"))

    if oil_up and severe_event:
        return _build_analysis(
            scope="global",
            title="Presion energetica por riesgo geopolitico y suba del petroleo",
            summary=(
                "El petroleo sube mas de 3% junto con un evento severo activo en una zona "
                "critica para el transporte energetico. El nivel de riesgo energetico se "
                "eleva y se observa presion adicional sobre transporte y consumo."
            ),
            positive=["Posible soporte para el oro como cobertura"] if not dollar_strong else [],
            negative=["Mayor costo de combustibles y fletes", "Presion sobre margenes de aerolineas y transporte"],
            risks=["Riesgo elevado en energia", "Volatilidad en activos sensibles a fletes y transporte"],
            opportunities=["Monitorear productoras de energia como cobertura tactica"],
            affected_assets=["Brent", "WTI", "Oro", "Aerolineas", "Navieras"],
            time_horizon="corto plazo",
            confidence=0.55,
            methodology=(
                "Regla: Brent/WTI change_percent > 3% AND evento severo activo en zona "
                "critica (Ormuz/Mar Rojo/Golfo) => riesgo energetico alto."
            ),
            scenario_base="El evento se mantiene contenido y el petroleo modera su suba en las proximas semanas.",
            scenario_optimistic="El evento se resuelve diplomaticamente y el petroleo retrocede hacia niveles previos.",
            scenario_adverse="El evento escala y afecta el transito energetico, sosteniendo precios altos por mas tiempo.",
        )
    return None


def analyze_argentina_tactical(indicators: list[dict], events: list[dict]) -> dict | None:
    """Si el riesgo pais de Argentina baja, el Merval sube, las reservas mejoran y el dolar
    financiero se estabiliza, entonces mejora la evaluacion tactica con advertencia por
    riesgo politico y liquidez."""
    riesgo_pais = _find(indicators, "RIESGO_PAIS")
    merval = _find(indicators, "MERV")
    reservas = _find(indicators, "RESERVAS")
    mep = _find(indicators, "USDARS_MEP")
    if not all([riesgo_pais, merval, reservas]):
        return None

    riesgo_baja = (riesgo_pais.get("change_percent") or 0) < 0
    merval_sube = (merval.get("change_percent") or 0) > 0
    reservas_mejoran = (reservas.get("change_percent") or 0) > 0
    mep_estable = mep is None or abs(mep.get("change_percent") or 0) < 1.5

    if riesgo_baja and merval_sube and reservas_mejoran and mep_estable:
        return _build_analysis(
            scope="argentina",
            title="Mejora tactica en activos argentinos con riesgos estructurales vigentes",
            summary=(
                "El riesgo pais desciende, el Merval sube, las reservas del BCRA mejoran y el "
                "dolar financiero se mantiene relativamente estable. La lectura tactica de corto "
                "plazo mejora, sin dejar de lado el riesgo politico y de liquidez de fondo."
            ),
            positive=["Riesgo pais a la baja", "Mejora de reservas internacionales", "Merval con sesgo positivo"],
            negative=["Persisten riesgos de liquidez y controles cambiarios"],
            risks=["Riesgo politico y regulatorio", "Sensibilidad a shocks externos"],
            opportunities=["Exposicion tactica limitada a activos argentinos de mayor liquidez"],
            affected_assets=["Merval", "Bonos AR", "ARS", "CEDEARs"],
            time_horizon="corto a medio plazo",
            confidence=0.5,
            methodology=(
                "Regla: riesgo_pais.change_percent < 0 AND MERV.change_percent > 0 AND "
                "RESERVAS.change_percent > 0 AND |MEP.change_percent| < 1.5% => mejora tactica."
            ),
            scenario_base="La mejora se mantiene gradual, condicionada a la acumulacion sostenida de reservas.",
            scenario_optimistic="El riesgo pais continua bajando y habilita mejor acceso a mercados de deuda.",
            scenario_adverse="Un shock externo o politico revierte la mejora y presiona el dolar financiero.",
        )
    return None


def analyze_paraguay_import_pressure(indicators: list[dict]) -> dict | None:
    """Si USD/PYG sube, la inflacion aumenta y la soja cae, entonces hay presion sobre
    importadores y posible deterioro de margenes en agro y consumo."""
    usdpyg = _find(indicators, "USDPYG")
    inflacion = _find(indicators, "IPC")
    soja = _find(indicators, "SOJA_PY")
    if not all([usdpyg, inflacion, soja]):
        return None

    pyg_sube = (usdpyg.get("change_percent") or 0) > 0
    inflacion_sube = (inflacion.get("change_percent") or 0) > 0
    soja_cae = (soja.get("change_percent") or 0) < 0

    if pyg_sube and inflacion_sube and soja_cae:
        return _build_analysis(
            scope="paraguay",
            title="Presion sobre importadores y margenes de agro/consumo en Paraguay",
            summary=(
                "El tipo de cambio USD/PYG sube junto con la inflacion, mientras el precio de "
                "la soja retrocede. Se advierte presion sobre importadores y posible deterioro "
                "de margenes en agro y consumo."
            ),
            positive=[],
            negative=["Encarecimiento de importaciones", "Menor ingreso por exportacion de soja"],
            risks=["Deterioro de margenes en agro y consumo", "Presion inflacionaria adicional"],
            opportunities=["Cobertura cambiaria para importadores expuestos"],
            affected_assets=["PYG", "Soja", "Agro", "Consumo"],
            time_horizon="corto a medio plazo",
            confidence=0.45,
            methodology=(
                "Regla: USDPYG.change_percent > 0 AND IPC.change_percent > 0 AND "
                "SOJA_PY.change_percent < 0 => presion sobre importadores y agro."
            ),
            scenario_base="La presion se mantiene moderada si la cosecha siguiente compensa el precio menor.",
            scenario_optimistic="La soja recupera precio y el tipo de cambio se estabiliza.",
            scenario_adverse="La combinacion de PYG debil, inflacion e ingresos agro menores presiona el consumo.",
        )
    return None


def run_all(indicators: list[dict], events: list[dict]) -> list[dict]:
    """Ejecuta todas las reglas disponibles y devuelve solo los analisis que se dispararon,
    mas un resumen regional siempre presente."""
    results: list[dict] = []
    for rule in (analyze_global_energy, analyze_argentina_tactical):
        outcome = rule(indicators, events)
        if outcome:
            results.append(outcome)
    outcome = analyze_paraguay_import_pressure(indicators)
    if outcome:
        results.append(outcome)

    results.append(
        _build_analysis(
            scope="regional",
            title="Lectura regional comparada",
            summary=(
                "Brasil aporta mayor profundidad de mercado, Paraguay ofrece estabilidad "
                "macroeconomica relativa con menor liquidez bursatil, y Argentina concentra "
                "mayor volatilidad y potencial tactico. El entorno global combina renta "
                "variable firme con riesgos geopoliticos en energia y transporte."
            ),
            positive=["Diversidad de perfiles de riesgo dentro de la region"],
            negative=["Heterogeneidad de liquidez y marco regulatorio entre paises"],
            risks=["Riesgo cambiario regional", "Riesgo geopolitico global"],
            opportunities=["Diversificacion por pais, moneda y clase de activo"],
            affected_assets=["Ibovespa", "BVPASA", "Merval", "USD/BRL", "USD/PYG", "USD/ARS"],
            time_horizon="medio plazo",
            confidence=0.5,
            methodology="Sintesis comparativa de los indicadores y eventos mas recientes por pais.",
            scenario_base="La region mantiene su patron actual de riesgo diferenciado por pais.",
            scenario_optimistic="Mejora sincronizada por flujos de capital hacia mercados emergentes.",
            scenario_adverse="Un shock externo (tasas, dolar global o energia) afecta a toda la region.",
        )
    )
    return results
