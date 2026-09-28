# Fase 4 — Orquestación controlada SIC-BA

Este módulo introduce un **control plane** para los jobs J01–J10 sin conectar todavía fuentes externas ni escribir en producción.

## Objetivo

Validar orden, inputs y gates antes de habilitar conectores reales. El runner es puro: no modifica Google Drive, ERP, PostgreSQL ni archivos de negocio.

## Ejecución

```bash
python run_f4.py \
  --manifest config/f4_manifest.example.json \
  --mode dry-run \
  --pretty
```

Pruebas:

```bash
python -m unittest tests/test_f4_orchestration.py
```

## Modos

- `dry-run`: los bloqueos esperados no producen error de proceso. Es el modo por defecto.
- `stage`: cualquier input/gate bloqueado deja la ejecución en estado `BLOCKED`.
- `apply`: mantiene los mismos gates y además exige el interlock explícito `SIC_BA_PRODUCTION_WRITE=ENABLED` para que J10 pueda considerarse habilitable.

> El runner actual **no contiene código de escritura productiva**, aun cuando todos los gates estén habilitados.

## Jobs

| Job | Función | Gate principal |
| --- | --- | --- |
| J01 | Ingesta ventas | input de ventas validado |
| J02 | Ingesta compras | calidad + período explícito |
| J03 | Ingesta pipeline | conflictos preservados |
| J04 | Descubrimiento OC/remisiones | no inferir vínculo |
| J05 | Resolución cliente/proveedor | exacto; fuzzy solo candidato |
| J06 | Candidatos cotización→venta/OC | nunca auto-confirmar |
| J07 | Candidatos costo→venta | evidencia de ítem/OC |
| J08 | Refresh BI | no publicar métricas N/D |
| J09 | Precheck financiero | L4 PASS |
| J10 | Cutover package | L4 + L7 + rollback + aprobación + interlock |

## Guardrails

1. Ningún input ausente se transforma en cero o dato confirmado.
2. Un candidato no se promueve automáticamente a confirmado.
3. Sin evidencia de ítem/OC, un costo queda `NO_ASIGNABLE`.
4. Finanzas permanece bloqueada si L4 no está en PASS.
5. Cutover permanece bloqueado si L4/L7 no están habilitados.
6. El modo `apply` requiere además rollback real, aprobación humana e interlock explícito.
7. No almacenar credenciales, tokens, IDs privados ni datos financieros internos en este repositorio público.

## Integración futura

Los conectores reales deben implementar adaptadores fuera de la lógica de gates. La función `evaluate_job()` debe permanecer pura para que las reglas puedan probarse sin acceso a producción.

Orden recomendado:

1. Adaptador de fuentes read-only.
2. Persistencia en staging/sandbox.
3. Audit log por `run_id`.
4. Idempotencia/upsert.
5. Quarantine/rejected.
6. Rollback de staging probado.
7. Recién después: revisión del gate de producción.
