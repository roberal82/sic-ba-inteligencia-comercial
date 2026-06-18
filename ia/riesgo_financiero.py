"""
SIC-BA IA - Riesgo Financiero v1.0

Calcula semáforo de liquidez con base en cobros, pagos y cheques próximos.
"""

from dataclasses import dataclass


@dataclass
class FlujoFinanciero:
    cobros_30d: float
    pagos_30d: float
    cheques_30d: float
    saldo_bancario: float = 0


def calcular_posicion_caja(flujo: FlujoFinanciero) -> dict:
    salidas = flujo.pagos_30d + flujo.cheques_30d
    posicion = flujo.saldo_bancario + flujo.cobros_30d - salidas
    ratio = (flujo.cobros_30d + flujo.saldo_bancario) / salidas if salidas else 999

    if ratio >= 1.20:
        semaforo = "VERDE"
        recomendacion = "Liquidez suficiente. Mantener control normal."
    elif ratio >= 1.00:
        semaforo = "AMARILLO"
        recomendacion = "Atención. Priorizar cobranzas y renegociar pagos no críticos."
    else:
        semaforo = "ROJO"
        recomendacion = "Riesgo de déficit. Activar gestión intensiva de cobranza y reprogramar salidas."

    return {
        "cobros_30d": flujo.cobros_30d,
        "pagos_30d": flujo.pagos_30d,
        "cheques_30d": flujo.cheques_30d,
        "saldo_bancario": flujo.saldo_bancario,
        "salidas_totales": salidas,
        "posicion_caja": posicion,
        "ratio_liquidez": round(ratio, 2),
        "semaforo": semaforo,
        "recomendacion": recomendacion,
    }


if __name__ == "__main__":
    ejemplo = FlujoFinanciero(
        cobros_30d=270_771_808,
        pagos_30d=180_000_000,
        cheques_30d=133_590_395,
        saldo_bancario=0,
    )
    print(calcular_posicion_caja(ejemplo))
