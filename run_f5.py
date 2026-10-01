"""Simulador de cutover F5 sin mutaciones externas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.cutover.models import CutoverContext
from src.cutover.simulator import simulate_cutover


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIC-BA F5 cutover dry-run")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("El manifest F5 debe ser un objeto JSON.")

    fields = CutoverContext.__dataclass_fields__
    unknown = set(payload) - set(fields)
    if unknown:
        raise SystemExit(f"Campos F5 desconocidos: {sorted(unknown)}")

    ctx = CutoverContext(**{name: bool(payload.get(name, False)) for name in fields})
    result = simulate_cutover(ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["overall"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
