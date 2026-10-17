"""Fase 2: valida registros de datos/validados/AAAA-MM-DD.json contra reglas de trazabilidad
y compara con el informe anterior (datos/historico)."""
import datetime as dt
from .config import RAIZ
from .util import cargar, corte

REQ = ["institucion", "titulo", "url", "fecha_publicacion", "fecha_medicion", "localidad",
       "indicador", "valor", "unidad", "tipo", "estado", "bloque"]
TIPOS = {"observado", "pronostico", "historico", "no_confirmado"}
ESTADOS = {"VERIFICADO", "PARCIALMENTE VERIFICADO", "NO VERIFICADO"}

def _dt(s):
    return dt.datetime.fromisoformat(s) if s else None

def validar(registros, fecha):
    lim = corte(fecha); ok, rech = [], []
    for r in registros:
        falt = [c for c in REQ if r.get(c) in (None, "")]
        if falt: rech.append((r, f"campos faltantes: {falt}")); continue
        if r["tipo"] not in TIPOS or r["estado"] not in ESTADOS: rech.append((r, "tipo/estado inválido")); continue
        if not str(r["url"]).startswith("http"): rech.append((r, "URL no verificable")); continue
        if r["estado"] == "NO VERIFICADO": rech.append((r, "no verificado: no se usa como hecho")); continue
        pub = _dt(r["fecha_publicacion"] + ("T" + r["hora_publicacion"] if r.get("hora_publicacion") else "T00:00"))
        if pub.tzinfo is None: pub = pub.replace(tzinfo=lim.tzinfo)
        if r.get("hora_publicacion") and pub > lim: rech.append((r, "posterior al corte")); continue
        if not r.get("hora_publicacion"):
            r["nota"] = "Hora de publicación no especificada: no puede confirmarse disponibilidad antes del corte."
            if r["estado"] == "VERIFICADO": r["estado"] = "PARCIALMENTE VERIFICADO"
        ok.append(r)
    return ok, rech

def anterior(fecha):
    h = RAIZ / "datos" / "historico"
    previos = sorted(p for p in h.glob("*.json") if p.stem < str(fecha))
    return (previos[-1].stem, cargar(previos[-1])) if previos else (None, None)

def comparar(registros, fecha):
    f0, prev = anterior(fecha); out = []
    idx = {(r["localidad"], r["indicador"], r["unidad"]): r for r in (prev or [])}
    for r in registros:
        if r["tipo"] != "observado": continue
        p = idx.get((r["localidad"], r["indicador"], r["unidad"]))
        row = {"localidad": r["localidad"], "indicador": r["indicador"], "unidad": r["unidad"],
               "actual": r["valor"], "fecha_actual": r["fecha_medicion"],
               "anterior": None, "fecha_anterior": None, "variacion": None,
               "texto": "NO SE DISPONE DE DATOS HOMOGÉNEOS PARA VERIFICAR LA VARIACIÓN."}
        if p and isinstance(p["valor"], (int, float)) and isinstance(r["valor"], (int, float)):
            v = round(r["valor"] - p["valor"], 4)
            row.update(anterior=p["valor"], fecha_anterior=p["fecha_medicion"], variacion=v)
            row["texto"] = ("SIN VARIACIÓN MATERIAL RESPECTO AL REPORTE ANTERIOR." if v == 0 else
                f'{r["localidad"]}: {p["valor"]} → {r["valor"]} {r["unidad"]} | {v:+g} {r["unidad"]}')
        out.append(row)
    return f0, out
