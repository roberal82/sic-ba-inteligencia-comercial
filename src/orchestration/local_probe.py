from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCAL_FILES = {
    "sales_ready": "fact_ventas.csv",
    "purchases_ready": "fact_compras.csv",
    "pipeline_ready": "pipeline_cotizaciones.csv",
}


def csv_has_data(path: Path) -> bool:
    """Devuelve True si existe un CSV con al menos una fila de datos."""
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)  # header
            return next(reader, None) is not None
    except (OSError, UnicodeError, csv.Error):
        return False


def build_local_manifest(data_clean: Path, run_id: str | None = None) -> dict[str, Any]:
    detected = {
        key: csv_has_data(data_clean / filename)
        for key, filename in LOCAL_FILES.items()
    }

    manifest_run_id = run_id or datetime.now(timezone.utc).strftime(
        "F4-LOCAL-%Y%m%dT%H%M%SZ"
    )

    return {
        "run_id": manifest_run_id,
        "inputs": {
            **detected,
            "purchases_incomplete_period": False,
            "pipeline_has_conflicts": False,
            # Estos dominios requieren fuentes/evidencia que el probe local no debe inferir.
            "documents_ready": False,
            "master_resolution_ready": False,
            "relation_candidates_ready": False,
            "cost_evidence_ready": False,
            "bi_ready": all(detected.values()),
        },
        "gates": {
            # Los gates financieros/productivos nunca se derivan de la presencia de archivos.
            "l4_pass": False,
            "l7_go": False,
            "rollback_real_proven": False,
            "human_approval": False,
        },
        "probe": {
            "data_clean": str(data_clean),
            "detected_files": LOCAL_FILES,
            "policy": "read-only; no infiere gates ni evidencia documental",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un manifest F4 read-only desde data_clean local."
    )
    parser.add_argument(
        "--data-clean",
        type=Path,
        default=Path("data_clean"),
        help="Directorio con CSV limpios. Default: data_clean",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Archivo JSON de salida. Si se omite, imprime a stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_local_manifest(args.data_clean, args.run_id)
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
