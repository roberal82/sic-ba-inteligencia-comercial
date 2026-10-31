"""Formato esperado: igual a cobros pero con encabezado 'CUENTAS A PAGAR' y 'PROVEEDOR:'."""
from __future__ import annotations

import re

from ..models import Pago
from ..money import parse_fecha, parse_monto

_FILA = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(\S+)\s+(\d{2}/\d{2}/\d{4})\s+([\d.,]+)\s+([\d.,]+)$"
)


def detectar(texto: str) -> bool:
    return "CUENTAS A PAGAR" in texto.upper()


def parsear(texto: str, fuente: str = "") -> list[Pago]:
    prov, moneda, filas = None, "PYG", []
    for linea in (" ".join(l.split()) for l in texto.splitlines()):
        if linea.upper().startswith("PROVEEDOR:"):
            prov = linea.split(":", 1)[1].strip()
        elif linea.upper().startswith("MONEDA:"):
            moneda = linea.split(":", 1)[1].strip().upper()
        elif (m := _FILA.match(linea)) and prov:
            emi, num, ven, total, saldo = m.groups()
            filas.append(Pago(prov, num, parse_fecha(emi), parse_fecha(ven),
                              moneda, parse_monto(total), parse_monto(saldo), fuente))
    return filas
