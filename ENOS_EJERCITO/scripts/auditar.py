"""Fase 4: control de calidad automático. Código de salida != 0 si falla algún control."""
import re, sys
from PIL import Image
from .config import RAIZ, ESCUDO
from .util import ahora, cargar, corte

def main(fecha=None):
    from .util import ahora; fecha = fecha or ahora().date(); s = str(fecha)
    d = RAIZ / "reportes" / s; fallos, avisos = [], []
    esperados = [d / f"{n}_ENOS_{s}.{e}" for n, e in [("RESUMEN", "txt"), ("REPORTE", "pdf"), ("DASHBOARD", "html"), ("FUENTES", "json"), ("COMPARATIVO", "csv")]]
    esperados.append(RAIZ / "infografias" / f"INFOGRAFIA_ENOS_{s}.png")
    for p in esperados:
        if not p.exists() or p.stat().st_size == 0: fallos.append(f"falta entregable {p.name}")
    png = RAIZ / "infografias" / f"INFOGRAFIA_ENOS_{s}.png"
    if png.exists():
        w, h = Image.open(png).size
        if (w, h) != (2160, 3840): fallos.append(f"resolución {w}x{h} != 2160x3840")
    fu = cargar(d / f"FUENTES_ENOS_{s}.json", {})
    lim = corte(fecha).isoformat()
    for r in fu.get("registros_validados", []):
        if not r.get("url"): fallos.append(f"registro sin URL: {r.get('indicador')}")
        if r.get("hora_publicacion") and r["fecha_publicacion"] + "T" + r["hora_publicacion"] > lim[:19]: fallos.append("registro posterior al corte")
    txt = (d / f"RESUMEN_ENOS_{s}.txt").read_text(encoding="utf-8") if esperados[0].exists() else ""
    if not (ESCUDO.exists()): avisos.append("ESCUDO ORIGINAL AUSENTE: no puede verificarse integridad ni las diez medallas")
    else: avisos.append("Escudo presente: verificación de las diez medallas requiere revisión visual humana")
    if not fu.get("registros_validados"): avisos.append("Sin registros validados: producto sin datos oficiales")
    n = len(txt.split())
    if n > 450: avisos.append(f"resumen largo ({n} palabras)")
    ca = [k for k, v in fu.get("estado_fuentes", {}).items() if v.get("estado") != "ACCESIBLE"]
    if ca: avisos.append(f"fuentes no accesibles/no localizadas: {', '.join(ca)}")
    print("AUDITORÍA", s); [print(" FALLO:", f) for f in fallos]; [print(" AVISO:", a) for a in avisos]
    sin = not fu.get("registros_validados")
    print(" RESULTADO:", "RECHAZADO" if fallos else ("NO PUBLICABLE: sin datos oficiales verificados" if sin else "APROBADO CON AVISOS"))
    return 1 if fallos else 0

if __name__ == "__main__":
    sys.exit(main())
