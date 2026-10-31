"""Cubre el hueco del original: parser de cheques diferidos.

Formato esperado (ajustar al export real):

    CHEQUES DIFERIDOS
    MONEDA: PYG
    000123 | BANCO X | PROVEEDOR SA | 15/03/2026 | 5.000.000
"""
from __future__ import annotations

from ..models import Cheque
from ..money import parse_fecha, parse_monto


def detectar(texto: str) -> bool:
    return "CHEQUES DIFERIDOS" in texto.upper()


def parsear(texto: str, fuente: str = "") -> list[Cheque]:
    moneda, filas = "PYG", []
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea.upper().startswith("MONEDA:"):
            moneda = linea.split(":", 1)[1].strip().upper()
            continue
        partes = [p.strip() for p in linea.split("|")]
        if len(partes) == 5:
            num, banco, benef, ven, monto = partes
            filas.append(Cheque(num, banco, benef, parse_fecha(ven), moneda, parse_monto(monto), fuente))
    return filas
