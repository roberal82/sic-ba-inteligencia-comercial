from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MONEDAS = {"PYG", "USD"}


@dataclass(frozen=True)
class Cobro:
    cliente: str
    comprobante: str
    emision: date
    vencimiento: date
    moneda: str
    total: float
    saldo: float
    fuente: str = ""

    def __post_init__(self) -> None:
        _validar(self.cliente, self.moneda, self.total, self.saldo)


@dataclass(frozen=True)
class Pago:
    proveedor: str
    numero: str
    emision: date
    vencimiento: date
    moneda: str
    total: float
    saldo: float
    fuente: str = ""

    def __post_init__(self) -> None:
        _validar(self.proveedor, self.moneda, self.total, self.saldo)


@dataclass(frozen=True)
class Cheque:
    numero: str
    banco: str
    beneficiario: str
    vencimiento: date
    moneda: str
    monto: float
    fuente: str = ""

    def __post_init__(self) -> None:
        _validar(self.beneficiario, self.moneda, self.monto, 0)


def _validar(nombre: str, moneda: str, total: float, saldo: float) -> None:
    if not nombre.strip():
        raise ValueError("nombre vacio")
    if moneda not in MONEDAS:
        raise ValueError(f"moneda invalida: {moneda}")
    if total < 0 or saldo < 0:
        raise ValueError("montos negativos")
