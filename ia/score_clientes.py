"""
SIC-BA IA - Score de Clientes v1.0

Calcula una puntuación 0-100 para cada cliente usando variables comerciales y financieras.
"""

from dataclasses import dataclass


@dataclass
class ClienteMetricas:
    cliente: str
    volumen_compra: float
    frecuencia_compra: float
    puntualidad_pago: float
    antiguedad: float
    margen: float


PESOS = {
    "volumen_compra": 0.30,
    "frecuencia_compra": 0.20,
    "puntualidad_pago": 0.25,
    "antiguedad": 0.10,
    "margen": 0.15,
}


def limitar(valor: float, minimo: float = 0, maximo: float = 100) -> float:
    return max(minimo, min(maximo, valor))


def clasificar_score(score: float) -> str:
    if score >= 90:
        return "Cliente Estratégico"
    if score >= 80:
        return "Cliente Premium"
    if score >= 70:
        return "Cliente Estable"
    if score >= 60:
        return "Cliente en Observación"
    return "Cliente de Riesgo"


def calcular_score_cliente(metricas: ClienteMetricas) -> dict:
    score = (
        limitar(metricas.volumen_compra) * PESOS["volumen_compra"]
        + limitar(metricas.frecuencia_compra) * PESOS["frecuencia_compra"]
        + limitar(metricas.puntualidad_pago) * PESOS["puntualidad_pago"]
        + limitar(metricas.antiguedad) * PESOS["antiguedad"]
        + limitar(metricas.margen) * PESOS["margen"]
    )

    return {
        "cliente": metricas.cliente,
        "score_total": round(score, 2),
        "clasificacion": clasificar_score(score),
        "componentes": {
            "volumen_compra": metricas.volumen_compra,
            "frecuencia_compra": metricas.frecuencia_compra,
            "puntualidad_pago": metricas.puntualidad_pago,
            "antiguedad": metricas.antiguedad,
            "margen": metricas.margen,
        },
    }


if __name__ == "__main__":
    ejemplo = ClienteMetricas(
        cliente="AGRIPLUS S.A.",
        volumen_compra=85,
        frecuencia_compra=80,
        puntualidad_pago=75,
        antiguedad=70,
        margen=82,
    )
    print(calcular_score_cliente(ejemplo))
