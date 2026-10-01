"""Ejecutor F4 local con persistencia aislada por run_id.

No conecta Google Drive, ERP ni base productiva.

Ejecutar:
    python run_f4_sandbox.py --manifest config/f4_manifest.example.json \
        --sandbox-root sandbox/f4 --mode dry-run

Rollback de un run:
    python run_f4_sandbox.py --sandbox-root sandbox/f4 \
        --rollback-run F4-DRYRUN-EXAMPLE
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.orchestration.models import Mode
from src.orchestration.runner import load_manifest, run_manifest
from src.orchestration.sandbox import SandboxRunStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIC-BA F4 sandbox local")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--sandbox-root", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in Mode],
        default=Mode.DRY_RUN.value,
    )
    parser.add_argument("--rollback-run", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = SandboxRunStore(args.sandbox_root)

    if args.rollback_run:
        removed = store.rollback(args.rollback_run)
        print(json.dumps({"run_id": args.rollback_run, "removed": removed}))
        return 0

    if args.manifest is None:
        raise SystemExit("--manifest es obligatorio salvo con --rollback-run")

    manifest = load_manifest(args.manifest)
    run_id = str(manifest.get("run_id", "")).strip()
    if not run_id:
        raise SystemExit("El manifest debe incluir run_id para sandbox.")

    run_dir, created = store.begin(run_id, manifest)
    result = run_manifest(manifest, Mode(args.mode))
    store.write_result(run_id, result)
    store.mark_completed(run_id, result["overall"])

    print(
        json.dumps(
            {
                "run_id": run_id,
                "created": created,
                "run_dir": str(run_dir),
                "overall": result["overall"],
            },
            ensure_ascii=False,
        )
    )

    if result["overall"] == "FAIL":
        return 1
    if result["overall"] == "BLOCKED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
