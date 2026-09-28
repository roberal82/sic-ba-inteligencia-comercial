from __future__ import annotations

from .models import CutoverContext, StepOutcome, StepResult


def simulate_cutover(ctx: CutoverContext) -> dict:
    """Simula el runbook F5 sin ejecutar ninguna mutación externa."""
    steps: list[StepResult] = []

    steps.append(StepResult(1, "Snapshot final de fuentes y ERP legacy", StepOutcome.PASS if ctx.snapshot_ready else StepOutcome.NOT_EXECUTED, "Snapshot disponible." if ctx.snapshot_ready else "Snapshot final no generado todavía.", "RP-01"))
    steps.append(StepResult(2, "Freeze de escritura legacy", StepOutcome.PASS if ctx.cutover_window_authorized else StepOutcome.BLOCKED_WINDOW, "Ventana autorizada." if ctx.cutover_window_authorized else "No existe ventana de cutover autorizada; no congelar legacy.", "RP-01"))
    steps.append(StepResult(3, "Carga de maestros/transacciones no financieras", StepOutcome.PASS if ctx.nonfinancial_ready else StepOutcome.NOT_EXECUTED, "Dominio no financiero listo." if ctx.nonfinancial_ready else "Falta readiness no financiero.", "RP-02"))
    steps.append(StepResult(4, "Validación de cardinalidad, claves y relaciones", StepOutcome.PASS if ctx.cardinality_validated else StepOutcome.NOT_EXECUTED, "Cardinalidad/relaciones validadas." if ctx.cardinality_validated else "Validación final pendiente.", "RP-02"))

    steps.append(StepResult(5, "Carga financiera CxC/CxP/bancos/cheques", StepOutcome.PASS if ctx.l4_pass else StepOutcome.BLOCKED_L4, "L4 está en PASS; carga financiera puede entrar al siguiente gate." if ctx.l4_pass else "L4 NO-GO: prohibido cargar/publicar finanzas oficiales.", "RP-03"))

    if not ctx.smoke_nonfinancial_pass:
        step6 = StepResult(6, "Smoke test end-to-end", StepOutcome.NOT_EXECUTED, "Smoke test no ejecutado.", "RP-03")
    elif not ctx.l4_pass:
        step6 = StepResult(6, "Smoke test end-to-end", StepOutcome.PASS_PARTIAL, "Smoke no financiero PASS; cobertura financiera excluida por L4.", "RP-03")
    else:
        step6 = StepResult(6, "Smoke test end-to-end", StepOutcome.PASS, "Smoke end-to-end habilitado por L4.", "RP-03")
    steps.append(step6)

    steps.append(StepResult(7, "Aprobación UAT / aceptación", StepOutcome.PASS if ctx.uat_accepted else StepOutcome.BLOCKED_APPROVAL, "UAT aceptado." if ctx.uat_accepted else "Aceptación humana/UAT pendiente.", "RP-03"))

    if not ctx.snapshot_ready:
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.BLOCKED_PRECONDITION, "Snapshot final obligatorio no disponible.", "RP-04")
    elif not ctx.cutover_window_authorized:
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.BLOCKED_WINDOW, "Ventana de cutover no autorizada.", "RP-04")
    elif not (ctx.nonfinancial_ready and ctx.cardinality_validated and ctx.smoke_nonfinancial_pass):
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.BLOCKED_PRECONDITION, "Readiness no financiero, cardinalidad o smoke incompletos.", "RP-04")
    elif not ctx.l4_pass:
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.BLOCKED_L4, "L4 NO-GO bloquea producción antes de evaluar L7.", "RP-04")
    elif not ctx.l7_go:
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.BLOCKED_L7, "L7 no está en GO.", "RP-04")
    elif not ctx.rollback_real_proven:
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.BLOCKED_ROLLBACK, "Rollback real snapshot/restore no probado.", "RP-04")
    elif not (ctx.uat_accepted and ctx.human_approval):
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.BLOCKED_APPROVAL, "Falta UAT y/o aprobación final de Dirección.", "RP-04")
    else:
        step8 = StepResult(8, "Go-live ERP productivo", StepOutcome.PASS, "Todos los gates de simulación están habilitados. La función no ejecuta go-live real.", "RP-04")
    steps.append(step8)

    steps.append(StepResult(9, "Convivencia controlada", StepOutcome.PASS if (ctx.go_live_executed and ctx.coexistence_stable) else StepOutcome.NOT_STARTED, "Convivencia estable." if (ctx.go_live_executed and ctx.coexistence_stable) else "Depende de go-live real y período de estabilidad.", "RP-04"))

    legacy_can_archive = all([
        ctx.snapshot_ready,
        ctx.nonfinancial_ready,
        ctx.cardinality_validated,
        ctx.smoke_nonfinancial_pass,
        ctx.uat_accepted,
        ctx.go_live_executed,
        ctx.coexistence_stable,
        ctx.l4_pass,
        ctx.l7_go,
        ctx.rollback_real_proven,
        ctx.human_approval,
    ])
    steps.append(StepResult(10, "Archivar ADMINISTRACION 2026", StepOutcome.PASS if legacy_can_archive else StepOutcome.BLOCKED_LEGACY, "Legacy archivabile por gates." if legacy_can_archive else "Legacy debe permanecer ACTIVO hasta snapshot + readiness + UAT + go-live estable + L4/L7 + rollback + aprobación.", None))

    blocked = [step for step in steps if step.outcome.blocked]
    failed = [step for step in steps if step.outcome is StepOutcome.FAIL]
    overall = "FAIL" if failed else ("NO-GO" if blocked else "GO_SIMULATED")
    return {"overall": overall, "go_live_simulated": step8.outcome is StepOutcome.PASS, "legacy_archive_simulated": legacy_can_archive, "steps": [step.as_dict() for step in steps]}
