"""Score de cliente 0-100: volumen, frecuencia y mora (inversa). Siempre acotado a [0, 100]."""
from __future__ import annotations

from .reglas import Reglas


def normalizar(valores: dict[str, float], inverso: bool = False) -> dict[str, float]:
    if not valores:
        return {}
    lo, hi = min(valores.values()), max(valores.values())
    if hi == lo:
        return {k: 50.0 for k in valores}
    out = {k: (v - lo) / (hi - lo) * 100 for k, v in valores.items()}
    return {k: 100 - v for k, v in out.items()} if inverso else out


def score_clientes(
    volumen: dict[str, float], frecuencia: dict[str, float], mora: dict[str, float], reglas: Reglas
) -> list[dict]:
    """Entradas por cliente, ya expresadas en UNA moneda base (no mezclar PYG y USD)."""
    s = reglas["score"]
    clientes = set(volumen) | set(frecuencia) | set(mora)
    nv = normalizar({c: volumen.get(c, 0.0) for c in clientes})
    nf = normalizar({c: frecuencia.get(c, 0.0) for c in clientes})
    nm = normalizar({c: mora.get(c, 0.0) for c in clientes}, inverso=True)
    filas = []
    for c in clientes:
        total = nv[c] * s["peso_volumen"] + nf[c] * s["peso_frecuencia"] + nm[c] * s["peso_mora"]
        total = round(max(0.0, min(100.0, total)), 2)
        semaforo = "ROJO" if total < s["umbral_rojo"] else "VERDE" if total >= s["umbral_verde"] else "AMARILLO"
        filas.append({"cliente": c, "score": total, "semaforo": semaforo, "version_reglas": reglas.version})
    return sorted(filas, key=lambda f: -f["score"])
