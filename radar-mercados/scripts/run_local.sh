#!/usr/bin/env bash
# Ejecuta el backend localmente (sirviendo tambien el frontend) sin Docker.
set -euo pipefail
cd "$(dirname "$0")/../backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f ".env" ] && [ -f "../.env.example" ]; then
  cp ../.env.example .env
  echo "Se creo backend/.env a partir de .env.example. Edite las claves opcionales si corresponde."
fi

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

alembic upgrade head
echo "Iniciando Radar Regional de Mercados en http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
