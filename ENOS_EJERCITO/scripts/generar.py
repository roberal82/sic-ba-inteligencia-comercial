"""Fase 3: genera los seis entregables a partir de los MISMOS datos validados."""
import csv, base64, html, shutil, subprocess, sys, datetime as dt
from .config import RAIZ, ESCUDO, PALETA, FUENTES, ESTACIONES_PARAGUAY, PAISES
from .util import ahora, cargar, guardar, corte, logger
from .validar import validar, comparar

SIN = "SIN DATO VERIFICADO"
CHROME = next(iter(sorted(__import__("pathlib").Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))), None) \
    or shutil.which("chromium") or shutil.which("google-chrome")

def por_bloque(regs, b): return [r for r in regs if r["bloque"] == b]

def linea(r):
    t = {"observado": "obs.", "pronostico": "PRON.", "historico": "hist.", "no_confirmado": "no conf."}[r["tipo"]]
    return f'{r["localidad"]}: {r["valor"]} {r["unidad"]} ({t}, {r["fecha_medicion"]}; {r["institucion"]})'

def resumen_txt(fecha, regs, comp, f0, estado):
    e = lambda b: "; ".join(linea(r) for r in por_bloque(regs, b)) or SIN + "."
    var = "; ".join(c["texto"] for c in comp if c["variacion"]) or (
        "NO SE DISPONE DE DATOS HOMOGÉNEOS PARA VERIFICAR LA VARIACIÓN." )
    fuentes = "\n".join(f'- {r["institucion"]}: {r["url"]} ({r["fecha_publicacion"]})' for r in regs) or \
        "- Ningún documento oficial pudo consultarse o verificarse antes del corte."
    acc = [k for k, v in estado["fuentes"].items() if v["estado"] == "ACCESIBLE"]
    return f"""EJÉRCITO PARAGUAYO

RESUMEN DIARIO ENOS – {fecha:%d/%m/%Y} | 05:20 HOP

Situación ENOS y meteorológica: {e("enos")} {e("meteo")}

Situación hidrológica: Río Paraguay: {e("paraguay")} Río Paraná: {e("parana")} Yacyretá/Itaipú: {e("embalses")} Afectación: {e("humanitario")}

Situación regional: {e("regional")}

Variación principal vs. informe anterior ({f0 or "sin informe anterior"}): {var}

Evaluación: No se emiten conclusiones de riesgo sin datos verificados. La ausencia de datos no debe interpretarse como estabilidad. Fuentes consultables en esta ejecución: {", ".join(acc) or "ninguna"}.

Fuentes:
{fuentes}

VENCER O MORIR — COMPROMETIDO CON SU PUEBLO
"""

def tabla(regs, vacio):
    if not regs: return f'<div class="vacio">{vacio}</div>'
    f = "".join(f'<tr><td>{html.escape(r["localidad"])}</td><td>{html.escape(str(r["valor"]))} {html.escape(r["unidad"])}</td>'
                f'<td>{r["tipo"]}</td><td>{r["fecha_medicion"]}</td></tr>' for r in regs)
    return f"<table>{f}</table>"

CSS = f"""*{{box-sizing:border-box;margin:0}}body{{background:{PALETA['negro']};color:{PALETA['blanco']};font-family:Arial,Helvetica,sans-serif;width:1080px}}
.hd{{background:{PALETA['verde']};border-bottom:6px solid {PALETA['dorado']};padding:18px;text-align:center}}
.esc{{width:150px;height:150px;margin:0 auto 8px;display:flex;align-items:center;justify-content:center}}
.esc img{{max-width:150px;max-height:150px;object-fit:contain}}
.esc .falta{{border:3px dashed {PALETA['rojo']};color:{PALETA['rojo']};font-size:22px;font-weight:bold;padding:12px}}
h1{{color:{PALETA['dorado']};font-size:46px}}h2{{font-size:32px}}.sub{{font-size:26px;margin-top:4px}}
.b{{margin:9px 24px;padding:10px 20px;border-left:8px solid {PALETA['dorado']};background:{PALETA['verde']}}}
.b h3{{color:{PALETA['dorado']};font-size:28px;margin-bottom:4px}}.b p,td{{font-size:24px;line-height:1.35}}
table{{width:100%;border-collapse:collapse}}td{{padding:4px 6px;border-bottom:1px solid #1d4a3a}}
.vacio{{color:{PALETA['rojo']};font-weight:bold;font-size:26px}}.var{{border-left-color:{PALETA['amarillo']}}}
.var,.var h3,.var td,.var p{{color:{PALETA['amarillo']}!important}}
.ft{{background:{PALETA['verde']};border-top:6px solid {PALETA['dorado']};padding:16px;text-align:center;margin-top:10px}}
.ft .l{{color:{PALETA['dorado']};font-size:34px;font-weight:bold}}.ft .f{{font-size:17px;margin-top:10px;word-break:break-all}}"""

def esc_html():
    if ESCUDO.exists():
        b = base64.b64encode(ESCUDO.read_bytes()).decode()
        return f'<div class="esc"><img alt="Escudo del Ejército Paraguayo" src="data:image/jpeg;base64,{b}"></div>'
    return '<div class="esc"><div class="falta">ESCUDO ORIGINAL NO DISPONIBLE<br>(espacio reservado)</div></div>'

def infografia_html(fecha, regs, comp, f0):
    B = lambda b, v: tabla(por_bloque(regs, b), v)
    var = "".join(f"<p>{html.escape(c['texto'])}</p>" for c in comp) or f"<p>NO SE DISPONE DE DATOS HOMOGÉNEOS PARA VERIFICAR LA VARIACIÓN.</p>"
    reg = "".join(f"<tr><td>{p}</td><td>{'; '.join(linea(r) for r in regs if r['bloque']=='regional' and r['localidad']==p) or SIN}</td></tr>" for p in PAISES)
    fu = " · ".join(f"{v[0]}: {v[1]}" for k, v in FUENTES.items() if v[1] and k in {"DMH", "CPC", "OMM", "EBY", "ITAIPU", "SEN", "COE"})
    bl = [("1 · SITUACIÓN ENOS (NOAA/CPC, OMM)", B("enos", SIN)), ("2 · SITUACIÓN REGIONAL", f"<table>{reg}</table>"),
          ("3 · METEOROLOGÍA DE PARAGUAY", B("meteo", SIN)), ("4 · RÍO PARAGUAY", B("paraguay", SIN + " en estaciones")),
          ("5 · RÍO PARANÁ", B("parana", SIN)), ("6 · YACYRETÁ E ITAIPÚ", B("embalses", SIN)),
          ("7 · AFECTACIÓN HUMANITARIA", B("humanitario", SIN))]
    cuerpo = "".join(f'<div class="b"><h3>{t}</h3>{c}</div>' for t, c in bl)
    cuerpo += f'<div class="b var"><h3>8 · VARIACIÓN VS. REPORTE ANTERIOR ({f0 or "sin informe previo"})</h3>{var}</div>'
    cuerpo += '<div class="b"><h3>9 · EVALUACIÓN EJECUTIVA</h3><p>1. Sin datos verificados no se emiten conclusiones de riesgo.<br>2. La ausencia de datos no se interpreta como estabilidad.<br>3. Prioridad: restablecer el acceso a las fuentes oficiales y cargar registros trazables.</p></div>'
    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=1080"><title>INFOGRAFÍA ENOS {fecha}</title><style>{CSS}</style>
<div class="hd">{esc_html()}<h1>EJÉRCITO PARAGUAYO</h1><h2>INFORME HIDROMETEOROLÓGICO</h2><div class="sub">FENÓMENO EL NIÑO 2026–2027</div><div class="sub">Corte: {fecha:%d/%m/%Y} 05:20 HOP</div></div>
{cuerpo}<div class="ft"><div class="l">VENCER O MORIR</div><div class="l">COMPROMETIDO CON SU PUEBLO</div><div class="f">Fuentes: {fu}</div></div></html>"""

def chrome(args):
    if not CHROME: raise RuntimeError("Chromium no encontrado")
    subprocess.run([str(CHROME), "--headless", "--no-sandbox", "--disable-gpu", *args], check=True, timeout=120, capture_output=True)

def main(fecha=None):
    lg = logger(); fecha = fecha or ahora().date(); s = str(fecha)
    estado = cargar(RAIZ / "datos" / "fuentes" / f"estado_{s}.json") or {"fuentes": {}}
    crudos = cargar(RAIZ / "datos" / "validados" / f"{s}.json", [])
    regs, rech = validar(crudos, fecha)
    f0, comp = comparar(regs, fecha)
    sal = RAIZ / "reportes" / s; sal.mkdir(parents=True, exist_ok=True)
    (sal / f"RESUMEN_ENOS_{s}.txt").write_text(resumen_txt(fecha, regs, comp, f0, estado), encoding="utf-8")
    guardar(sal / f"FUENTES_ENOS_{s}.json", {"fecha": s, "corte": corte(fecha).isoformat(), "generado": ahora().isoformat(),
        "estado_fuentes": estado["fuentes"], "registros_validados": regs,
        "registros_rechazados": [{"registro": r, "motivo": m} for r, m in rech]})
    with open(sal / f"COMPARATIVO_ENOS_{s}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["localidad", "indicador", "unidad", "anterior", "fecha_anterior", "actual", "fecha_actual", "variacion", "texto"], extrasaction="ignore")
        w.writeheader(); w.writerows(comp)
    ih = infografia_html(fecha, regs, comp, f0)
    (sal / f"DASHBOARD_ENOS_{s}.html").write_text(ih, encoding="utf-8")
    ruta = (sal / f"DASHBOARD_ENOS_{s}.html").resolve().as_uri()
    png = RAIZ / "infografias" / f"INFOGRAFIA_ENOS_{s}.png"
    chrome([f"--screenshot={png}", "--window-size=1080,1920", "--force-device-scale-factor=2", "--hide-scrollbars", ruta])
    chrome([f"--print-to-pdf={sal / f'REPORTE_ENOS_{s}.pdf'}", "--no-pdf-header-footer", ruta])
    if crudos is not None and regs: guardar(RAIZ / "datos" / "historico" / f"{s}.json", regs)
    lg.info("Generado %s: %d válidos, %d rechazados", s, len(regs), len(rech))

if __name__ == "__main__":
    main()
