"""Formato esperado (documentado, ajustar al export real):

    REPORTE CUENTAS A COBRAR
    CLIENTE: ACME SA
    MONEDA: PYG
    01/02/2026 001-001-0000123 30/03/2026 1.000.000 400.000
"""
from __future__ import annotations

import re

from ..models import Cobro
from ..money import parse_fecha, parse_monto

_FILA = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(\S+)\s+(\d{2}/\d{2}/\d{4})\s+([\d.,]+)\s+([\d.,]+)$"
)


def detectar(texto: str) -> bool:
    return "CUENTAS A COBRAR" in texto.upper()


def parsear(texto: str, fuente: str = "") -> list[Cobro]:
    cliente, moneda, filas = None, "PYG", []
    for linea in (" ".join(l.split()) for l in texto.splitlines()):
        if linea.upper().startswith("CLIENTE:"):
            cliente = linea.split(":", 1)[1].strip()
        elif linea.upper().startswith("MONEDA:"):
            moneda = linea.split(":", 1)[1].strip().upper()
        elif (m := _FILA.match(linea)) and cliente:
            emi, comp, ven, total, saldo = m.groups()
            filas.append(Cobro(cliente, comp, parse_fecha(emi), parse_fecha(ven),
                               moneda, parse_monto(total), parse_monto(saldo), fuente))
    return filas
