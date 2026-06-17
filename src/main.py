"""
SIC-BA Extractor PDFs Valurq v1.0
Autor: Blanco & Asociados / Proyecto SIC-BA

Este script detecta reportes PDF del ERP Valurq y genera tablas base.
"""

from pathlib import Path
import re
import csv
import datetime as dt

try:
    import pdfplumber
except ImportError as exc:
    raise SystemExit("Instale dependencias: pip install pdfplumber pandas python-dateutil openpyxl") from exc


ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data_raw"
DATA_CLEAN = ROOT / "data_clean"


def read_pdf_text(pdf_path: Path) -> str:
    """Extrae texto de un PDF usando pdfplumber."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def parse_amount(value: str) -> float:
    """Convierte montos paraguayos tipo 1.234.567,89 a float."""
    if value is None:
        return 0.0
    value = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0


def detect_report_type(text: str) -> str:
    t = text.upper()
    if "PENDIENTES POR COBRAR" in t:
        return "pendientes_cobrar"
    if "REPORTE DE PENDIENTES A PAGAR" in t or "PENDIENTES A PAGAR" in t:
        return "pendientes_pagar"
    if "REPORTE DE COMPRAS" in t:
        return "compras"
    return "desconocido"


def parse_pendientes_cobrar(text: str, source_file: str) -> list[dict]:
    """Parser inicial para pendientes por cobrar de Valurq."""
    rows = []
    current_client = None
    current_currency = "GUARANIES"

    for line in text.splitlines():
        line_clean = " ".join(line.split())

        if "Moneda:" in line_clean:
            current_currency = "USD" if "DOLARES" in line_clean.upper() else "PYG"

        if "Teléfono:" in line_clean and not line_clean.startswith("Fecha "):
            current_client = line_clean.split("Teléfono:")[0].strip()

        m = re.search(
            r"(\d{2}/\d{2}/\d{4})\s+([0-9]{3}-[0-9]{3}-[0-9]{7})\s+(\S+)\s+(\d{2}/\d{2}/\d{4})\s+([\d\.\,]+)\s+([\d\.\,]+)",
            line_clean,
        )
        if m:
            fecha, comprobante, tipo, vencimiento, total, saldo = m.groups()
            rows.append({
                "fuente": source_file,
                "cliente": current_client or "",
                "comprobante": comprobante,
                "tipo": tipo,
                "fecha": fecha,
                "vencimiento": vencimiento,
                "moneda": current_currency,
                "total": parse_amount(total),
                "saldo": parse_amount(saldo),
            })

    return rows


def parse_pendientes_pagar(text: str, source_file: str) -> list[dict]:
    """Parser inicial para pendientes a pagar de Valurq."""
    rows = []
    current_provider = None
    current_currency = "PYG"

    for line in text.splitlines():
        line_clean = " ".join(line.split())

        if line_clean.startswith("Moneda :"):
            current_currency = "PYG" if "GUARANIES" in line_clean.upper() else line_clean.split(":")[-1].strip()

        if (
            line_clean
            and line_clean.upper() == line_clean
            and not any(x in line_clean for x in ["FECHA", "TOTAL", "TOTALES", "DESDE", "REPORTE", "BLANCO", "PAG."])
            and len(line_clean) > 3
        ):
            current_provider = line_clean.strip()

        m = re.search(
            r"(\d{2}/\d{2}/\d{4})\s+([A-Za-z0-9\-]+)\s+([\d\.\,]+)\s+([\d\.\,]+)\s+(\d{2}/\d{2}/\d{4})",
            line_clean,
        )
        if m and current_provider:
            fecha, numero, total_factura, saldo, vencimiento = m.groups()
            rows.append({
                "fuente": source_file,
                "proveedor": current_provider,
                "numero": numero,
                "fecha": fecha,
                "vencimiento": vencimiento,
                "moneda": current_currency,
                "total_factura": parse_amount(total_factura),
                "saldo": parse_amount(saldo),
            })

    return rows


def parse_compras(text: str, source_file: str) -> list[dict]:
    """Parser inicial para reporte de compras por proveedor/producto."""
    rows = []
    current_provider = None

    for line in text.splitlines():
        line_clean = " ".join(line.split())

        if line_clean.startswith("Proveedor "):
            current_provider = line_clean.replace("Proveedor ", "").strip()

        m = re.search(r"(\d{2}/\d{2}/\d{4})\s+([A-Za-z0-9\-]+)\s+(\w+)\s+(.+?)\s+([\d\.\,]+)\s+([\d\.\,]+)$", line_clean)
        if m and current_provider:
            fecha, fac_nro, moneda, producto, cantidad, total = m.groups()
            rows.append({
                "fuente": source_file,
                "proveedor": current_provider,
                "fecha": fecha,
                "factura": fac_nro,
                "moneda": moneda,
                "producto": producto.strip(),
                "cantidad": parse_amount(cantidad),
                "total": parse_amount(total),
            })

    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA_CLEAN.mkdir(exist_ok=True)

    all_cobros = []
    all_pagos = []
    all_compras = []
    log_rows = []

    for pdf_path in DATA_RAW.glob("*.pdf"):
        text = read_pdf_text(pdf_path)
        report_type = detect_report_type(text)

        if report_type == "pendientes_cobrar":
            rows = parse_pendientes_cobrar(text, pdf_path.name)
            all_cobros.extend(rows)
        elif report_type == "pendientes_pagar":
            rows = parse_pendientes_pagar(text, pdf_path.name)
            all_pagos.extend(rows)
        elif report_type == "compras":
            rows = parse_compras(text, pdf_path.name)
            all_compras.extend(rows)
        else:
            rows = []

        log_rows.append({
            "archivo": pdf_path.name,
            "tipo_detectado": report_type,
            "registros": len(rows),
            "fecha_carga": dt.datetime.now().isoformat(timespec="seconds"),
        })

    write_csv(DATA_CLEAN / "fact_cobros.csv", all_cobros)
    write_csv(DATA_CLEAN / "fact_pagos.csv", all_pagos)
    write_csv(DATA_CLEAN / "fact_compras.csv", all_compras)
    write_csv(DATA_CLEAN / "log_carga.csv", log_rows)

    print("Carga terminada")
    print(f"Cobros: {len(all_cobros)}")
    print(f"Pagos: {len(all_pagos)}")
    print(f"Compras: {len(all_compras)}")


if __name__ == "__main__":
    main()
