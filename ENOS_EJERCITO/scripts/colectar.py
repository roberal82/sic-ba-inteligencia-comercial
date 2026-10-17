"""Fase 1: consulta cada fuente con reintentos y guarda instantánea + estado.
NO extrae valores: la extracción exige parsers verificados contra el documento real.
Los registros validados se cargan en datos/validados/AAAA-MM-DD.json (ver validar.py)."""
import hashlib, sys, time, datetime as dt, requests
from .config import FUENTES, RAIZ
from .util import ahora, corte, guardar, logger

def consultar(url, intentos=4):
    ultimo = None
    for i in range(intentos):
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "ENOS-Ejercito/1.0"})
            return r.status_code, r.content, None
        except requests.RequestException as e:
            ultimo = f"{type(e).__name__}: {str(e)[:200]}"
            time.sleep(2 ** (i + 1))
    return None, b"", ultimo

def main(fecha=None):
    lg = logger(); fecha = fecha or ahora().date()
    estado = {"fecha": str(fecha), "consulta": ahora().isoformat(), "corte": corte(fecha).isoformat(), "fuentes": {}}
    for k, (inst, url, metodo) in FUENTES.items():
        if not url:
            estado["fuentes"][k] = {"institucion": inst, "estado": "NO_LOCALIZADA", "metodo": metodo}
            lg.warning("%s: canal oficial no localizado", k); continue
        t = ahora().isoformat()
        code, cuerpo, err = consultar(url)
        e = {"institucion": inst, "url": url, "consulta": t, "http": code, "error": err, "metodo": metodo,
             "estado": "ACCESIBLE" if code and code < 400 else "INACCESIBLE"}
        if cuerpo and code and code < 400:
            e["sha256"] = hashlib.sha256(cuerpo).hexdigest()
            d = RAIZ / "datos" / "fuentes" / str(fecha); d.mkdir(parents=True, exist_ok=True)
            (d / f"{k}.html").write_bytes(cuerpo)
        estado["fuentes"][k] = e
        lg.info("%s -> %s %s", k, code, err or "")
    guardar(RAIZ / "datos" / "fuentes" / f"estado_{fecha}.json", estado)
    return estado

if __name__ == "__main__":
    main()
