"""SIC-BA Motor de Alertas con gobierno financiero fail-closed."""

from pathlib import Path
import pandas as pd
import datetime as dt

from src.financial_governance import load_financial_gate

ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = ROOT / "data_clean"


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_CLEAN / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def add_alert(alerts: list[dict], nivel: str, modulo: str, titulo: str, detalle: str, accion: str, monto: float = 0) -> None:
    alerts.append({
        "fecha_generacion": dt.datetime.now().isoformat(timespec="seconds"),
        "nivel": nivel,
        "modulo": modulo,
        "titulo": titulo,
        "detalle": detalle,
        "accion_recomendada": accion,
        "monto_referencia": round(float(monto), 2),
    })


def generar_alertas(financial_official: bool | None = None) -> pd.DataFrame:
    hoy = pd.Timestamp.today().normalize()
    alerts: list[dict] = []
    if financial_official is None:
        financial_official = load_financial_gate(DATA_CLEAN).official

    cobros = load_csv("fact_cobros.csv")
    pagos = load_csv("fact_pagos.csv")
    cheques = load_csv("fact_cheques.csv")
    ventas = load_csv("fact_ventas.csv")
    score = load_csv("score_clientes.csv")

    # Finanzas solo participa con gate L4 oficial. Sin gate, se ignoran completamente
    # saldos, vencimientos y cheques para evitar acciones sobre datos provisionales.
    if financial_official:
        if not cobros.empty and {"cliente", "vencimiento", "saldo"}.issubset(cobros.columns):
            cobros = cobros.copy()
            cobros["saldo"] = to_num(cobros["saldo"])
            cobros["fecha_vencimiento"] = to_date(cobros["vencimiento"])
            cobros["dias_vencido"] = (hoy - cobros["fecha_vencimiento"]).dt.days
            vencidos = cobros[(cobros["dias_vencido"] > 0) & (cobros["saldo"] > 0)]
            if not vencidos.empty:
                top = vencidos.groupby("cliente", dropna=False).agg(
                    saldo=("saldo", "sum"),
                    max_dias=("dias_vencido", "max"),
                    facturas=("saldo", "count"),
                ).sort_values("saldo", ascending=False).head(10).reset_index()
                for _, r in top.iterrows():
                    nivel = "ROJO" if r["max_dias"] >= 30 or r["saldo"] >= 20_000_000 else "AMARILLO"
                    add_alert(
                        alerts, nivel, "Cobranza", f"Vencimiento documentado: {r['cliente']}",
                        f"Saldo vencido Gs {r['saldo']:,.0f}. Máximo atraso {r['max_dias']:.0f} días. Facturas: {r['facturas']:.0f}.",
                        "Revisar evidencia y gestionar cobranza según política aprobada.", r["saldo"]
                    )

        if not pagos.empty and {"proveedor", "vencimiento", "saldo"}.issubset(pagos.columns):
            pagos = pagos.copy()
            pagos["saldo"] = to_num(pagos["saldo"])
            pagos["fecha_vencimiento"] = to_date(pagos["vencimiento"])
            pagos["dias_a_vencer"] = (pagos["fecha_vencimiento"] - hoy).dt.days
            proximos = pagos[(pagos["dias_a_vencer"] >= 0) & (pagos["dias_a_vencer"] <= 7) & (pagos["saldo"] > 0)]
            if not proximos.empty:
                top_p = proximos.groupby("proveedor", dropna=False).agg(
                    saldo=("saldo", "sum"), vencimiento_min=("fecha_vencimiento", "min"), facturas=("saldo", "count")
                ).sort_values("saldo", ascending=False).head(10).reset_index()
                for _, r in top_p.iterrows():
                    add_alert(
                        alerts, "AMARILLO", "Proveedores", f"Pago documentado próximo: {r['proveedor']}",
                        f"Saldo a vencer Gs {r['saldo']:,.0f}. Vencimiento más cercano: {r['vencimiento_min'].date()}.",
                        "Confirmar programación y disponibilidad de caja conciliada.", r["saldo"]
                    )

        if not cheques.empty:
            fecha_col = "vencimiento" if "vencimiento" in cheques.columns else "vence" if "vence" in cheques.columns else None
            if fecha_col and "monto" in cheques.columns:
                cheques = cheques.copy()
                cheques["monto"] = to_num(cheques["monto"])
                cheques["fecha_vencimiento"] = to_date(cheques[fecha_col])
                cheques["dias_a_vencer"] = (cheques["fecha_vencimiento"] - hoy).dt.days
                prox_ch = cheques[(cheques["dias_a_vencer"] >= 0) & (cheques["dias_a_vencer"] <= 7) & (cheques["monto"] > 0)]
                for _, r in prox_ch.sort_values("monto", ascending=False).head(10).iterrows():
                    beneficiario = r.get("beneficiario", "Beneficiario no informado")
                    add_alert(
                        alerts, "ROJO", "Tesorería", f"Cheque documentado próximo: {beneficiario}",
                        f"Monto Gs {r['monto']:,.0f}. Vence: {r['fecha_vencimiento'].date()}.",
                        "Verificar débito/programación y fondeo contra banco conciliado.", r["monto"]
                    )

    # Score es comercial mientras no exista un modelo financiero aprobado.
    if not score.empty and {"cliente", "score_cliente"}.issubset(score.columns):
        score = score.copy()
        score["score_cliente"] = to_num(score["score_cliente"])
        if 'score_tipo' in score.columns:
            comerciales = score[score['score_tipo'].astype(str).eq('COMERCIAL_NO_FINANCIERO')]
            for _, r in comerciales[comerciales["score_cliente"] < 50].sort_values("score_cliente").head(5).iterrows():
                add_alert(
                    alerts, "INFO", "Comercial", f"Baja actividad relativa: {r['cliente']}",
                    f"Score comercial: {r['score_cliente']:.1f}. No representa riesgo de mora o crédito.",
                    "Revisar frecuencia/recurrencia y oportunidad comercial; no usar para bloquear crédito.", 0
                )

    # Concentración comercial se basa exclusivamente en ventas documentadas.
    if not ventas.empty and {"cliente", "total_gs"}.issubset(ventas.columns):
        ventas = ventas.copy()
        ventas["total_gs"] = to_num(ventas["total_gs"])
        total = ventas["total_gs"].sum()
        if total > 0:
            conc = ventas.groupby("cliente", dropna=False)["total_gs"].sum().sort_values(ascending=False).reset_index()
            conc["participacion"] = conc["total_gs"] / total * 100
            for _, r in conc[conc["participacion"] >= 25].head(5).iterrows():
                add_alert(
                    alerts, "AMARILLO", "Comercial", f"Alta concentración en cliente: {r['cliente']}",
                    f"Representa {r['participacion']:.1f}% de las ventas detectadas.",
                    "Diversificar cartera y abrir oportunidades en clientes B y C.", r["total_gs"]
                )

    return pd.DataFrame(alerts)


def generar_reporte_md(alertas: pd.DataFrame) -> str:
    hoy = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = ["# REPORTE EJECUTIVO SIC-BA", f"Fecha de generación: {hoy}", "", "## Resumen", f"Alertas generadas: {len(alertas)}", ""]
    if alertas.empty:
        lines.append("No se generaron alertas habilitadas con los datos y gates actuales.")
        return "\n".join(lines)
    resumen = alertas.groupby(["nivel", "modulo"], dropna=False).size().reset_index(name="cantidad")
    lines.append("## Alertas por nivel y módulo")
    for _, r in resumen.iterrows():
        lines.append(f"- {r['nivel']} | {r['modulo']}: {r['cantidad']}")
    lines.extend(["", "## Principales alertas"])
    principales = alertas.sort_values("monto_referencia", ascending=False).head(15)
    for _, r in principales.iterrows():
        lines.extend([f"### {r['nivel']} - {r['titulo']}", f"**Módulo:** {r['modulo']}", f"**Detalle:** {r['detalle']}", f"**Acción:** {r['accion_recomendada']}", ""])
    return "\n".join(lines)


def main() -> None:
    DATA_CLEAN.mkdir(exist_ok=True)
    gate = load_financial_gate(DATA_CLEAN)
    alertas = generar_alertas(financial_official=gate.official)
    (DATA_CLEAN / "alertas.csv").write_text(alertas.to_csv(index=False), encoding="utf-8-sig")
    (DATA_CLEAN / "reporte_ejecutivo_diario.md").write_text(generar_reporte_md(alertas), encoding="utf-8")
    print(f"Alertas generadas: {len(alertas)} | finanzas_oficiales={gate.official}")


if __name__ == "__main__":
    main()
