from __future__ import annotations

from collections.abc import Mapping

from .models import ExecutionContext, JobResult, JobSpec, Mode, Outcome


JOBS: tuple[JobSpec, ...] = (
    JobSpec("J01", "Ingesta ventas", "sales_ready"),
    JobSpec("J02", "Ingesta compras", "purchases_ready"),
    JobSpec("J03", "Ingesta pipeline", "pipeline_ready"),
    JobSpec("J04", "Descubrimiento OC/remisiones", "documents_ready"),
    JobSpec("J05", "Resolución cliente/proveedor", "master_resolution_ready"),
    JobSpec("J06", "Candidatos cotización→venta/OC", "relation_candidates_ready"),
    JobSpec(
        "J07",
        "Candidatos costo→venta",
        "cost_evidence_ready",
        requires_cost_evidence=True,
    ),
    JobSpec("J08", "Refresh BI", "bi_ready"),
    JobSpec("J09", "Precheck financiero L4", financial=True),
    JobSpec("J10", "Cutover package"),
)


def _truthy_input(inputs: Mapping[str, object], key: str | None) -> bool:
    if key is None:
        return True
    return bool(inputs.get(key, False))


def evaluate_job(
    spec: JobSpec,
    ctx: ExecutionContext,
    inputs: Mapping[str, object],
) -> JobResult:
    """Evalúa un job sin ejecutar mutaciones externas.

    Esta función es deliberadamente pura: no toca Drive, ERP, base de datos ni archivos.
    Sirve para validar el orden de ejecución y los gates antes de integrar conectores reales.
    """

    if spec.job_id == "J09":
        if not ctx.l4_pass:
            return JobResult(
                spec.job_id,
                spec.name,
                Outcome.BLOCKED_L4,
                "L4 permanece NO-GO; no cargar ni publicar CxC/CxP/bancos/cheques.",
            )
        return JobResult(
            spec.job_id,
            spec.name,
            Outcome.PASS,
            "Gate L4 disponible para precheck financiero.",
        )

    if spec.job_id == "J10":
        if not ctx.l4_pass:
            return JobResult(
                spec.job_id,
                spec.name,
                Outcome.BLOCKED_L4,
                "L4 permanece NO-GO; cutover productivo bloqueado antes de L7.",
            )
        if not ctx.l7_go:
            return JobResult(
                spec.job_id,
                spec.name,
                Outcome.BLOCKED_L7,
                "L7 no está en GO; cutover productivo bloqueado.",
            )
        if not ctx.rollback_real_proven or not ctx.human_approval:
            return JobResult(
                spec.job_id,
                spec.name,
                Outcome.BLOCKED_L7,
                "Faltan rollback real probado y/o aprobación humana final.",
            )
        if ctx.mode is Mode.APPLY and not ctx.production_write_enabled:
            return JobResult(
                spec.job_id,
                spec.name,
                Outcome.BLOCKED_PROD_INTERLOCK,
                "Interlock de escritura productiva no habilitado explícitamente.",
            )
        return JobResult(
            spec.job_id,
            spec.name,
            Outcome.PASS,
            "Cutover habilitable por gates; este runner no ejecuta escrituras externas.",
        )

    if spec.job_id == "J07":
        if bool(inputs.get("cost_evidence_ready", False)):
            return JobResult(
                spec.job_id,
                spec.name,
                Outcome.PASS,
                "Evidencia de costo completa disponible para el alcance declarado; asignar únicamente relaciones documentadas.",
            )
        if bool(inputs.get("cost_evidence_partial", False)):
            return JobResult(
                spec.job_id,
                spec.name,
                Outcome.PASS_WITH_EXCEPTIONS,
                "Existe evidencia parcial de ítem/OC: solo los ítems documentados pueden recibir costo. Los restantes quedan NO_ASIGNABLE y no se publica margen total de la operación.",
            )
        return JobResult(
            spec.job_id,
            spec.name,
            Outcome.BLOCKED_INPUT,
            "Input requerido no disponible: cost_evidence_ready. Sin evidencia de ítem/OC el costo debe quedar NO_ASIGNABLE.",
        )

    if not _truthy_input(inputs, spec.input_key):
        detail = f"Input requerido no disponible: {spec.input_key}."
        if spec.requires_cost_evidence:
            detail += " Sin evidencia de ítem/OC el costo debe quedar NO_ASIGNABLE."
        return JobResult(spec.job_id, spec.name, Outcome.BLOCKED_INPUT, detail)

    if spec.job_id == "J02" and bool(inputs.get("purchases_incomplete_period", False)):
        return JobResult(
            spec.job_id,
            spec.name,
            Outcome.PASS_WITH_EXCEPTIONS,
            "Compras cargables con período incompleto explícitamente marcado; ausencia no equivale a cero.",
        )

    if spec.job_id == "J03" and bool(inputs.get("pipeline_has_conflicts", False)):
        return JobResult(
            spec.job_id,
            spec.name,
            Outcome.PASS_WITH_EXCEPTIONS,
            "Pipeline cargable conservando conflictos/revisiones en cola; no fusionar automáticamente.",
        )

    return JobResult(
        spec.job_id,
        spec.name,
        Outcome.PASS,
        "Input disponible; validación de control superada.",
    )
