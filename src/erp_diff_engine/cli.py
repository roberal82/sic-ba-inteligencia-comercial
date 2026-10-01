"""CLI del ERP_DIFF_ENGINE.

Ejemplo:
    python run_erp_diff.py --base BASE.xlsx --current CURRENT.xlsx --output out/
    python run_erp_diff.py --config config/erp_diff.example.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .engine import run
from .security import EngineInputError, EngineSecurityError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "ERP_DIFF_ENGINE: compara dos workbooks Excel (BASE vs CURRENT) sin "
            "escribir producción. Fase A: uso exclusivo con fixtures sintéticos."
        )
    )
    parser.add_argument("--config", type=Path, default=None, help="Archivo de configuración JSON.")
    parser.add_argument("--base", type=Path, default=None, help="Ruta al archivo BASE (.xlsx).")
    parser.add_argument("--current", type=Path, default=None, help="Ruta al archivo CURRENT (.xlsx).")
    parser.add_argument(
        "--output", type=Path, default=None, help="Directorio de salida de los reportes."
    )
    parser.add_argument(
        "--log-file", type=Path, default=None, help="Archivo de log opcional (además de stderr)."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    overrides = {
        "base_path": str(args.base) if args.base else None,
        "current_path": str(args.current) if args.current else None,
        "output_dir": str(args.output) if args.output else None,
        "log_file": str(args.log_file) if args.log_file else None,
    }
    try:
        config = load_config(args.config, overrides)
        result = run(config)
    except (EngineInputError, EngineSecurityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - error controlado en el borde CLI; nunca aborta silenciosamente
        print(f"ERROR inesperado: {exc}", file=sys.stderr)
        return 1

    print(f"OK: {result.total_differences} diferencias detectadas.")
    for name, path in sorted(result.output_files.items()):
        print(f"  {name}: {path}")
    for classification, count in sorted(result.counts_by_classification.items()):
        print(f"  {classification}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
