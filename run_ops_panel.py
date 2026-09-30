"""Panel de operación SIC-BA: agrega TECHNICAL/L4/L7/WRITER/ROLLBACK/CUTOVER/
PRODUCTION/ADMIN 2026 en una sola vista de solo lectura."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ops_panel import build_panel, render_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIC-BA operational status panel (read-only)")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Salida en JSON en lugar de tabla de texto")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = build_panel(config)
    if args.json:
        print(json.dumps([row.__dict__ for row in rows], ensure_ascii=False, indent=2))
    else:
        print(render_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
