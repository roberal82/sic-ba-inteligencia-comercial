"""Runner seguro de Fase 4.

Por defecto solo simula. El modo apply se rechaza mientras los gates de
producción no estén todos habilitados.
"""
from typing import Iterable, List

from .config import Gates, Mode
from .contracts import JobContext, JobResult
from .jobs import JOBS_BY_ID, validate_catalog


class GateError(RuntimeError):
    pass


def _guard_mode(mode: Mode, gates: Gates) -> None:
    if mode is Mode.APPLY and not gates.production_ready:
        raise GateError(
            "MODE=apply bloqueado: requiere L4 PASS, L7 GO, rollback real probado "
            "y aprobación de Dirección"
        )


def simulate_job(job_id: str, context: JobContext, gates: Gates) -> JobResult:
    validate_catalog()
    spec = JOBS_BY_ID[job_id]
    mode = Mode(context.mode)
    _guard_mode(mode, gates)

    if spec.requires_l4 and not gates.l4_finanzas:
        return JobResult(
            job_id=job_id,
            status="BLOCKED_EXPECTED_L4",
            details={"reason": "L4 NO-GO", "notes": spec.notes},
        )
    if spec.requires_l7 and not gates.l7_release:
        return JobResult(
            job_id=job_id,
            status="BLOCKED_EXPECTED_L7",
            details={"reason": "L7 BLOQUEADO", "notes": spec.notes},
        )

    if job_id == "J07":
        return JobResult(
            job_id=job_id,
            status="NO_ASIGNABLE",
            details={"reason": "Falta evidencia ítem/OC para asignar costo real"},
        )

    return JobResult(
        job_id=job_id,
        status="PASS_SIM_CONTROL",
        details={"notes": spec.notes},
    )


def run_jobs(job_ids: Iterable[str], context: JobContext, gates: Gates) -> List[JobResult]:
    return [simulate_job(job_id, context, gates) for job_id in job_ids]
