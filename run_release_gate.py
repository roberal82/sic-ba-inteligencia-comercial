"""Evalúa readiness del Release Candidate sin ejecutar cutover productivo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.orchestration.release_gate import evaluate_release_candidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIC-BA Release Candidate gate")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    result = evaluate_release_candidate(payload).as_dict()
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
        )
    )
    return 0 if result["technical_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
