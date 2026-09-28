"""Catálogo de jobs F4 y sus barreras de seguridad."""
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    name: str
    requires_l4: bool = False
    requires_l7: bool = False
    permits_inference: bool = False
    notes: str = ""


JOB_SPECS: Tuple[JobSpec, ...] = (
    JobSpec("J01", "MASTER_CLIENTES_PROVEEDORES", notes="No inferir RUC; excepciones a cuarentena."),
    JobSpec("J02", "PIPELINE_COTIZACIONES", notes="Preservar conflictos, revisiones y colisiones."),
    JobSpec("J03", "FACTURA_VENTA", notes="NRO_FACTURA es atributo legal; excluir CxC oficial."),
    JobSpec("J04", "FACTURA_COMPRA", notes="Alcance Jan-Ago; septiembre incompleto."),
    JobSpec("J05", "OC_ENTREGAS", notes="Vincular solo evidencia explícita; preservar versiones."),
    JobSpec("J06", "RELACIONES_COMERCIALES", notes="CANDIDATA nunca se auto-confirma."),
    JobSpec("J07", "ASIGNACION_COSTO", notes="Sin ítem/OC/evidencia => NO_ASIGNABLE."),
    JobSpec("J08", "REFRESH_BI", notes="Margen real/caja quedan N/D si faltan gates."),
    JobSpec("J09", "PRECHECK_L4", requires_l4=True, notes="Validar homogeneidad; no completar huecos."),
    JobSpec("J10", "PRECHECK_CUTOVER", requires_l4=True, requires_l7=True, notes="Solo GO/NO-GO; no ejecuta producción."),
)

JOBS_BY_ID: Dict[str, JobSpec] = {j.job_id: j for j in JOB_SPECS}


def validate_catalog() -> None:
    ids = [j.job_id for j in JOB_SPECS]
    if len(ids) != 10 or len(set(ids)) != 10:
        raise ValueError("F4 requiere exactamente J01-J10 con IDs únicos")
    if any(j.permits_inference for j in JOB_SPECS):
        raise ValueError("Ningún job F4 puede habilitar inferencia como hecho confirmado")
