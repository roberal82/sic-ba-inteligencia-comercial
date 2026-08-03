"""Perfiles de asignacion orientativa por escenario. Son definiciones metodologicas fijas
(no cotizaciones), por lo que no dependen de APP_MODE ni de fuentes externas."""
from app.services.fallback_service import demo_scenarios


def get_scenarios() -> list[dict]:
    return demo_scenarios()
