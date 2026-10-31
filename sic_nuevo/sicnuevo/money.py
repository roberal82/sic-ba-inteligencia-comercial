from __future__ import annotations

from datetime import date, datetime


def parse_monto(texto: str) -> float:
    """Convierte '1.234.567,89' (formato es-PY) a float. Lanza ValueError si no es numerico."""
    limpio = texto.strip().replace(".", "").replace(",", ".")
    return float(limpio)


def parse_fecha(texto: str) -> date:
    return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
