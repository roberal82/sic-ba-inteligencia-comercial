from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .jobs import JOBS, evaluate_job
from .models import ExecutionContext, Mode, Outcome


PRODUCTION_INTERLOCK_VALUE = "ENABLED"


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("El manifest debe ser un objeto JSON.")
    return payload


def build_context(manifest: dict[str, Any], mode: Mode) -> ExecutionContext:
    gates = manifest.get("gates", {}) or {}
    if not isinstance(gates, dict):
        raise ValueError("manifest.gates debe ser un objeto JSON.")

    production_write_enabled = (
        os.getenv("SIC_BA_PRODUCTION_WRITE", "").strip().upper()
        == PRODUCTION_INTERLOCK_VALUE
    )

    return ExecutionContext(
        mode=mode,
        l4_pass=bool(gates.get("l4_pass", False)),
        l7_go=bool(gates.get("l7_go", False)),
        rollback_real_proven=bool(gates.get("rollback_real_proven", False)),
        human_approval=bool(gates.get("human_approval", False)),
        production_write_enabled=production_write_enabled,
    )


def run_manifest(manifest: dict[str, Any], mode: Mode) -> dict[str, Any]:
    inputs = manifest.get("inputs", {}) or {}
    if not isinstance(inputs, dict):
        raise ValueError("manifest.inputs debe ser un objeto JSON.")

    ctx = build_context(manifest, mode)
    results = [evaluate_job(spec, ctx, inputs) for spec in JOBS]

    blocked = [r for r in results if r.outcome.is_blocked]
    failed = [r for r in results if r.outcome is Outcome.FAIL]

    if failed:
        overall = "FAIL"
    elif blocked:
        overall = "PASS_WITH_EXPECTED_BLOCKS" if mode is Mode.DRY_RUN else "BLOCKED"
    else:
        overall = "PASS"

    return {
        "run_id": str(manifest.get("run_id", "F4-UNSPECIFIED")),
        "mode": mode.value,
        "overall": overall,
        "production_ready": ctx.production_ready,
        "production_write_interlock": ctx.production_write_enabled,
        "results": [result.as_dict() for result in results],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SIC-BA F4: evaluador de jobs/gates sin mutaciones externas."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Ruta al manifest JSON de inputs y gates.",
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in Mode],
        default=Mode.DRY_RUN.value,
        help="dry-run por defecto. stage/apply endurecen el tratamiento de bloqueos.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Imprime JSON indentado.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    result = run_manifest(manifest, Mode(args.mode))

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=False,
        )
    )

    if result["overall"] == "FAIL":
        return 1
    if result["overall"] == "BLOCKED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
