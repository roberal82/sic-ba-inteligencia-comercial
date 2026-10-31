"""Alertas por reglas configurables. Los montos se agregan por moneda, nunca mezclados."""
from __future__ import annotations

import sqlite3
from datetime import date

from .reglas import Reglas


def _alerta(nivel, modulo, titulo, monto, moneda, reglas: Reglas) -> dict:
    return {"nivel": nivel, "modulo": modulo, "titulo": titulo, "monto": monto,
            "moneda": moneda, "version_reglas": reglas.version}


def alertas_cobranza(con: sqlite3.Connection, hoy: date, reglas: Reglas) -> list[dict]:
    c = reglas["cobranza"]
    filas = con.execute(
        """SELECT cliente, moneda, SUM(saldo) saldo, MIN(vencimiento) mas_antiguo
           FROM cobros WHERE saldo > 0 AND vencimiento < ? GROUP BY cliente, moneda""",
        (hoy.isoformat(),),
    ).fetchall()
    out = []
    for f in filas:
        dias = (hoy - date.fromisoformat(f["mas_antiguo"])).days
        rojo = dias >= c["dias_rojo"] or f["saldo"] >= c["monto_rojo"].get(f["moneda"], float("inf"))
        out.append(_alerta("ROJO" if rojo else "AMARILLO", "Cobranza",
                           f"Vencido {dias} dias: {f['cliente']}", f["saldo"], f["moneda"], reglas))
    return sorted(out, key=lambda a: (a["nivel"] != "ROJO", -a["monto"]))


def alertas_vencimientos(con: sqlite3.Connection, hoy: date, reglas: Reglas) -> list[dict]:
    dias = reglas["vencimientos"]["ventana_dias"]
    desde, hasta = hoy.toordinal(), hoy.toordinal() + dias
    ini, fin = date.fromordinal(desde).isoformat(), date.fromordinal(hasta).isoformat()
    out = []
    for f in con.execute(
        "SELECT proveedor, moneda, SUM(saldo) s FROM pagos WHERE saldo>0 AND vencimiento BETWEEN ? AND ? GROUP BY proveedor, moneda",
        (ini, fin)):
        out.append(_alerta("AMARILLO", "Proveedores", f"Pago proximo: {f['proveedor']}", f["s"], f["moneda"], reglas))
    for f in con.execute(
        "SELECT beneficiario, moneda, SUM(monto) s FROM cheques WHERE vencimiento BETWEEN ? AND ? GROUP BY beneficiario, moneda",
        (ini, fin)):
        out.append(_alerta("ROJO", "Tesoreria", f"Cheque proximo: {f['beneficiario']}", f["s"], f["moneda"], reglas))
    return out


def semaforo_liquidez(cobros_30d: float, salidas_30d: float, saldo_banco: float, reglas: Reglas) -> dict:
    l = reglas["liquidez"]
    ratio = (cobros_30d + saldo_banco) / salidas_30d if salidas_30d else float("inf")
    nivel = "VERDE" if ratio >= l["ratio_verde"] else "AMARILLO" if ratio >= l["ratio_amarillo"] else "ROJO"
    return {"ratio": ratio, "nivel": nivel, "posicion": saldo_banco + cobros_30d - salidas_30d}
