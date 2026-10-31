"""Uso: python -m sicnuevo.cli reporte.txt [...] --db sic.db   (acepta .txt o .pdf)"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from . import alertas, parsers, reglas, store


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("archivos", nargs="+")
    ap.add_argument("--db", default="sic.db")
    a = ap.parse_args(argv)
    reg, con = reglas.cargar_reglas(), store.abrir(a.db)
    for ruta in a.archivos:
        p = Path(ruta)
        texto = parsers.leer_pdf(p) if p.suffix.lower() == ".pdf" else p.read_text(encoding="utf-8")
        tipo = parsers.detectar(texto)
        if tipo is None:
            print(f"{p.name}: tipo no reconocido (se omite)")
            continue
        n = store.cargar(con, parsers.ADAPTADORES[tipo].parsear(texto, p.name))
        print(f"{p.name}: {tipo} -> {n} registros")
    hoy = date.today()
    for al in alertas.alertas_cobranza(con, hoy, reg) + alertas.alertas_vencimientos(con, hoy, reg):
        print(f"[{al['nivel']}] {al['modulo']}: {al['titulo']} ({al['moneda']} {al['monto']:,.0f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
