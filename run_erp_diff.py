"""Entrada simple para ERP_DIFF_ENGINE (Sprint 001, Fase A).

Ejemplos:
    python run_erp_diff.py --base BASE.xlsx --current CURRENT.xlsx --output out/
    python run_erp_diff.py --config config/erp_diff.example.json

No usar todavía contra BASE/CURRENT reales del ERP: Fase A es exclusivamente
para fixtures sintéticos, según AGENTS.md y SPRINT_001_ERP_DRIFT.md.
"""

from src.erp_diff_engine.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
