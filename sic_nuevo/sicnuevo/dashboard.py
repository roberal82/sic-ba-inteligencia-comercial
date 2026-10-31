"""Dashboard de solo lectura sobre SQLite, sin dependencias externas.

Uso: python -m sicnuevo.dashboard --db sic.db [--port 8000]
Escucha solo en 127.0.0.1. Agregar autenticacion antes de exponerlo en red.
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import alertas
from .reglas import Reglas, cargar_reglas

BUCKETS = [("Al dia", None, 0), ("1-30", 1, 30), ("31-60", 31, 60), ("61-90", 61, 90), ("90+", 91, None)]


def _monedas(con: sqlite3.Connection) -> list[str]:
    q = "SELECT moneda FROM cobros UNION SELECT moneda FROM pagos UNION SELECT moneda FROM cheques"
    return sorted(r[0] for r in con.execute(q))


def _aging(con: sqlite3.Connection, moneda: str, hoy: date) -> list[dict]:
    filas = con.execute(
        "SELECT vencimiento, saldo FROM cobros WHERE moneda=? AND saldo>0", (moneda,)
    ).fetchall()
    out = []
    for nombre, lo, hi in BUCKETS:
        total = 0.0
        for f in filas:
            dias = (hoy - date.fromisoformat(f["vencimiento"])).days
            if (lo is None or dias >= lo) and (hi is None or dias <= hi):
                total += f["saldo"]
        out.append({"tramo": nombre, "saldo": total})
    return out


def calcular(con: sqlite3.Connection, hoy: date, reglas: Reglas) -> dict:
    """Todos los montos se calculan por moneda; nunca se suman PYG con USD."""
    limite = (hoy + timedelta(days=30)).isoformat()
    por_moneda = {}
    for m in _monedas(con):
        def uno(sql, *p):
            return con.execute(sql, p).fetchone()[0] or 0.0

        cobros_30d = uno("SELECT SUM(saldo) FROM cobros WHERE moneda=? AND vencimiento<=?", m, limite)
        pagos_30d = uno("SELECT SUM(saldo) FROM pagos WHERE moneda=? AND vencimiento<=?", m, limite)
        cheques_30d = uno("SELECT SUM(monto) FROM cheques WHERE moneda=? AND vencimiento<=?", m, limite)
        por_moneda[m] = {
            "por_cobrar": uno("SELECT SUM(saldo) FROM cobros WHERE moneda=?", m),
            "vencido": uno("SELECT SUM(saldo) FROM cobros WHERE moneda=? AND vencimiento<?", m, hoy.isoformat()),
            "por_pagar": uno("SELECT SUM(saldo) FROM pagos WHERE moneda=?", m),
            "cheques": uno("SELECT SUM(monto) FROM cheques WHERE moneda=?", m),
            "liquidez": alertas.semaforo_liquidez(cobros_30d, pagos_30d + cheques_30d, 0.0, reglas),
            "aging": _aging(con, m, hoy),
            "top_deudores": [dict(r) for r in con.execute(
                "SELECT cliente, SUM(saldo) saldo FROM cobros WHERE moneda=? AND saldo>0 "
                "GROUP BY cliente ORDER BY saldo DESC LIMIT 5", (m,))],
        }
    return {
        "hoy": hoy.isoformat(),
        "version_reglas": reglas.version,
        "monedas": por_moneda,
        "alertas": alertas.alertas_cobranza(con, hoy, reglas) + alertas.alertas_vencimientos(con, hoy, reglas),
    }


def _n(v: float) -> str:
    return f"{v:,.0f}"


def _barras(items: list[tuple[str, float]]) -> str:
    mx = max((v for _, v in items), default=0) or 1
    filas = []
    for i, (et, v) in enumerate(items):
        w = v / mx * 220
        filas.append(
            f'<text x="0" y="{i*22+14}" font-size="12">{escape(et)}</text>'
            f'<rect x="90" y="{i*22+3}" width="{w:.0f}" height="14" fill="#2b6cb0"/>'
            f'<text x="{96+w:.0f}" y="{i*22+14}" font-size="11">{_n(v)}</text>'
        )
    return f'<svg width="520" height="{len(items)*22+4}" role="img">{"".join(filas)}</svg>'


_COLOR = {"ROJO": "#c53030", "AMARILLO": "#b7791f", "VERDE": "#2f855a"}


def render(d: dict) -> str:
    sec = []
    for m, x in d["monedas"].items():
        liq = x["liquidez"]
        ratio = "sin salidas" if liq["ratio"] == float("inf") else f"{liq['ratio']:.2f}"
        deudores = "".join(f"<tr><td>{escape(r['cliente'])}</td><td class=n>{_n(r['saldo'])}</td></tr>" for r in x["top_deudores"])
        sec.append(f"""<section><h2>{escape(m)}</h2>
<div class=kpis>
<div><b>{_n(x['por_cobrar'])}</b><span>Por cobrar</span></div>
<div><b>{_n(x['vencido'])}</b><span>Vencido</span></div>
<div><b>{_n(x['por_pagar'])}</b><span>Por pagar</span></div>
<div><b>{_n(x['cheques'])}</b><span>Cheques</span></div>
<div><b style="color:{_COLOR[liq['nivel']]}">{liq['nivel']}</b><span>Liquidez 30d (ratio {ratio})</span></div>
</div>
<h3>Antiguedad de cartera</h3>{_barras([(a['tramo'], a['saldo']) for a in x['aging']])}
<h3>Mayores deudores</h3><table>{deudores or '<tr><td>Sin saldos</td></tr>'}</table></section>""")
    al = "".join(
        f"<tr><td style='color:{_COLOR.get(a['nivel'], '#000')}'><b>{escape(a['nivel'])}</b></td>"
        f"<td>{escape(a['modulo'])}</td><td>{escape(a['titulo'])}</td>"
        f"<td class=n>{escape(a['moneda'])} {_n(a['monto'])}</td></tr>" for a in d["alertas"])
    return f"""<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>SIC nuevo</title><style>
body{{font-family:system-ui,sans-serif;margin:0 auto;max-width:960px;padding:16px;background:#fff;color:#1a202c}}
.kpis{{display:flex;flex-wrap:wrap;gap:12px}}.kpis div{{border:1px solid #cbd5e0;border-radius:6px;padding:8px 12px;min-width:140px}}
.kpis b{{display:block;font-size:20px}}.kpis span{{font-size:12px;color:#4a5568}}
table{{border-collapse:collapse;width:100%}}td{{border-bottom:1px solid #e2e8f0;padding:4px 8px}}.n{{text-align:right}}
@media(prefers-color-scheme:dark){{body{{background:#1a202c;color:#edf2f7}}.kpis div,td{{border-color:#4a5568}}.kpis span{{color:#a0aec0}}}}
</style><h1>SIC nuevo</h1><p>Fecha {escape(d['hoy'])} · reglas {escape(d['version_reglas'])}</p>
{''.join(sec) or '<p>Sin datos cargados.</p>'}
<h2>Alertas ({len(d['alertas'])})</h2><table>{al or '<tr><td>Sin alertas</td></tr>'}</table></html>"""


def servir(db: str, puerto: int) -> None:
    reglas = cargar_reglas()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            # Conexion de solo lectura, nueva por pedido (hilo seguro)
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            try:
                cuerpo = render(calcular(con, date.today(), reglas)).encode()
            finally:
                con.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *a):
            pass

    print(f"Dashboard en http://127.0.0.1:{puerto}")
    ThreadingHTTPServer(("127.0.0.1", puerto), H).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="sic.db")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    servir(a.db, a.port)
