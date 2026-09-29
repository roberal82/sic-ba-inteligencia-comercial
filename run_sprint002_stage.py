"""Sprint 002 — ejecución operacional read-only + staging aislado.

No conecta ERP/Drive/PostgreSQL productivo. Las únicas escrituras ocurren bajo
``--stage-root``. El rollback elimina exclusivamente el ``run_id`` indicado.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.orchestration.models import Mode
from src.orchestration.operational import rollback_operational_run, run_operational_stage
from src.orchestration.runner import load_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIC-BA Sprint 002 staging runner")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--source-root", type=Path, default=None)
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in Mode],
        default=Mode.STAGE.value,
    )
    parser.add_argument("--rollback-run", default=None)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.rollback_run:
        removed = rollback_operational_run(args.stage_root, args.rollback_run)
        print(json.dumps({"run_id": args.rollback_run, "removed": removed}))
        return 0

    if args.manifest is None or args.source_root is None:
        raise SystemExit("--manifest y --source-root son obligatorios salvo con --rollback-run")

    manifest = load_manifest(args.manifest)
    result = run_operational_stage(
        manifest,
        Mode(args.mode),
        args.source_root,
        args.stage_root,
    )
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
    if str(result["overall"]).startswith("BLOCKED"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
