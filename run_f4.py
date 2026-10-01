"""Entrada simple para la orquestación F4.

Ejemplo:
    python run_f4.py --manifest config/f4_manifest.example.json --mode dry-run --pretty
"""

from src.orchestration.runner import main


if __name__ == "__main__":
    raise SystemExit(main())
