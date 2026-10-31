"""Adaptadores por tipo de reporte. Cada uno expone detectar(texto) y parsear(texto, fuente)."""
from __future__ import annotations

from . import cheques, cobros, pagos

ADAPTADORES = {"cobros": cobros, "pagos": pagos, "cheques": cheques}


def detectar(texto: str) -> str | None:
    for nombre, mod in ADAPTADORES.items():
        if mod.detectar(texto):
            return nombre
    return None


def leer_pdf(ruta) -> str:
    """Lectura opcional de PDF; requiere pdfplumber instalado."""
    import pdfplumber

    with pdfplumber.open(ruta) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)
