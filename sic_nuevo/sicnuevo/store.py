"""Almacenamiento SQLite con carga idempotente (clave natural por tabla)."""
from __future__ import annotations

import sqlite3
from dataclasses import asdict

from .models import Cheque, Cobro, Pago

DDL = """
CREATE TABLE IF NOT EXISTS cobros (
  cliente TEXT NOT NULL, comprobante TEXT NOT NULL, emision TEXT, vencimiento TEXT NOT NULL,
  moneda TEXT NOT NULL, total REAL, saldo REAL, fuente TEXT,
  PRIMARY KEY (cliente, comprobante, moneda));
CREATE TABLE IF NOT EXISTS pagos (
  proveedor TEXT NOT NULL, numero TEXT NOT NULL, emision TEXT, vencimiento TEXT NOT NULL,
  moneda TEXT NOT NULL, total REAL, saldo REAL, fuente TEXT,
  PRIMARY KEY (proveedor, numero, moneda));
CREATE TABLE IF NOT EXISTS cheques (
  numero TEXT NOT NULL, banco TEXT NOT NULL, beneficiario TEXT, vencimiento TEXT NOT NULL,
  moneda TEXT NOT NULL, monto REAL, fuente TEXT,
  PRIMARY KEY (numero, banco));
"""

_TABLAS = {Cobro: "cobros", Pago: "pagos", Cheque: "cheques"}


def abrir(ruta: str = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    return con


def cargar(con: sqlite3.Connection, registros: list) -> int:
    """Upsert: recargar el mismo reporte no duplica filas. Devuelve filas procesadas."""
    for r in registros:
        d = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in asdict(r).items()}
        cols = ",".join(d)
        marcas = ",".join(f":{k}" for k in d)
        con.execute(f"INSERT OR REPLACE INTO {_TABLAS[type(r)]} ({cols}) VALUES ({marcas})", d)
    con.commit()
    return len(registros)
