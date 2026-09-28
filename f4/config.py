"""Configuración de seguridad para Fase 4 SIC-BA.

Producción permanece bloqueada por defecto. No guardar secretos aquí.
"""
from dataclasses import dataclass
from enum import Enum


class Mode(str, Enum):
    DRY_RUN = "dry-run"
    STAGE = "stage"
    APPLY = "apply"


@dataclass(frozen=True)
class Gates:
    l4_finanzas: bool = False
    l7_release: bool = False
    aprobacion_direccion: bool = False
    rollback_real_probado: bool = False

    @property
    def production_ready(self) -> bool:
        return all((
            self.l4_finanzas,
            self.l7_release,
            self.aprobacion_direccion,
            self.rollback_real_probado,
        ))


DEFAULT_GATES = Gates()
PRODUCTION_TARGET = "BlancoyAsociados_Sistema_Integral"
PRODUCTION_FILE_ID = "1k_gRk7ojd6kmFdjyZ86wD2zjLvruoppGYOGHkrCvv6Q"
FINANCIAL_CUTOFF = "2026-09-26T23:59:00-03:00"
RULESET_VERSION = "F4-2026.09.27-v1"
