from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

RUTA_DEFECTO = Path(__file__).resolve().parents[1] / "reglas.toml"


@dataclass(frozen=True)
class Reglas:
    raw: dict

    @property
    def version(self) -> str:
        return self.raw["version"]

    def __getitem__(self, k):
        return self.raw[k]


def cargar_reglas(ruta: Path | str = RUTA_DEFECTO) -> Reglas:
    with open(ruta, "rb") as f:
        raw = tomllib.load(f)
    s = raw["score"]
    if abs(s["peso_volumen"] + s["peso_frecuencia"] + s["peso_mora"] - 1.0) > 1e-9:
        raise ValueError("los pesos del score deben sumar 1.0")
    return Reglas(raw)
