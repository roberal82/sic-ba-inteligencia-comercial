# Sprint 003 — Release Candidate SIC-BA

## Objetivo

Cerrar el desarrollo técnico de la fase actual en un **Release Candidate de staging**, con regresión completa, gates explícitos y documentación operativa, sin habilitar producción.

## Estado esperado al cierre

- ERP Diff Engine validado.
- Control plane J01–J10 validado.
- Staging read-only + quarantine + audit + rollback validado.
- Full regression PASS.
- CI PASS.
- `technical_status = RC_READY`.
- Producción permanece bloqueada por L4/L7 mientras esos gates no estén aprobados.
- No existe writer productivo en este release candidate.

## Separación de readiness

El release gate distingue dos conceptos:

### Technical readiness

Requiere todos estos checks en PASS:

- `full_regression_pass`
- `orchestration_ci_pass`
- `drift_gate_pass`
- `staging_ci_pass`
- `rollback_test_pass`
- `no_private_data`

Cuando todos están en true, el estado técnico es:

`RC_READY`

### Production readiness

Es independiente del readiness técnico y exige:

1. L4 PASS;
2. L7 GO;
3. rollback real probado;
4. aprobación humana;
5. interlock `SIC_BA_PRODUCTION_WRITE=ENABLED`.

Aun si todos esos gates fueran true, Sprint 003 responde:

`GATES_READY_WRITER_ABSENT`

porque no contiene código de escritura productiva.

## Full regression

El workflow de Release Candidate ejecuta:

1. instalación mínima de dependencias de test;
2. `python -m compileall`;
3. suite completa `pytest -q`;
4. F4 orchestration smoke test;
5. Sprint 002 staging tests;
6. release gate con evidencia técnica positiva;
7. `git diff --check`.

## Ejecución local del gate

```bash
python run_release_gate.py \
  --evidence config/release_candidate.example.json \
  --pretty
```

Resultado esperado con L4/L7 bloqueados:

```text
technical_status: RC_READY
production_status: BLOCKED_L4
technical_ready: true
production_ready: false
writer_present: false
```

## Política de corte

Este sprint finaliza el **desarrollo y hardening del staging**. No autoriza:

- merge a `main`;
- actualización del ERP productivo;
- publicación de CxC/CxP/bancos/cheques sin L4;
- cutover sin L7;
- inferencia de costos o relaciones no documentadas.

## Condición de “terminado” del proyecto técnico actual

El proyecto se considera técnicamente terminado en staging cuando:

- Sprint 001 PASS e integrado;
- Sprint 002 PASS e integrado;
- Sprint 003 full regression PASS;
- release gate `RC_READY`;
- `main` intacto;
- producción intacta;
- los únicos bloqueos restantes corresponden a decisiones/gates externos: L4, L7 y autorización humana de cutover.
