# SIC-BA — Gate L4 (evidencia financiera oficial)

## Propósito

L4 es el interlock que decide si los datos financieros (CxC, CxP, cheques,
movimientos bancarios, conciliación nominal) pueden tratarse como **oficiales**
en cualquier flujo que dependa de ellos (writer productivo, cutover engine,
alertas financieras, márgenes reales). Implementado en
`src/gates/l4_evidence.py`.

## Regla dura

**Fail-closed siempre.** No existe ninguna combinación de campos que apruebe
el gate con datos ausentes. En particular, poner `l4_pass=true` (o el
equivalente) sin el resto de la evidencia **nunca** es suficiente —
`evaluate_l4()` ignora cualquier campo booleano suelto y exige el documento
completo.

## `FinancialGateEvidence` — campos obligatorios

| Campo | Tipo | Requisito para PASS |
|---|---|---|
| `cutoff` | `str` | No vacío (y debe igualar `expected_cutoff` si se pasa uno) |
| `cxc_status` | `EvidenceStatus` | `CONFIRMED` |
| `cxp_status` | `EvidenceStatus` | `CONFIRMED` |
| `checks_status` | `EvidenceStatus` | `CONFIRMED` |
| `bank_status` | `EvidenceStatus` | `CONFIRMED` |
| `nominal_reconciliation_status` | `EvidenceStatus` | `CONFIRMED` |
| `approved_by` | `str` | No vacío |
| `approval_timestamp` | `str` | No vacío |
| `evidence_refs` | `tuple[str, ...]` | No vacío |
| `source_hashes` | `Mapping[str, str]` | No vacío |

`EvidenceStatus` = `CONFIRMED` \| `CANDIDATE` \| `INSUFFICIENT_EVIDENCE` \|
`REQUIRES_HUMAN_REVIEW` (mismos estados que `AGENTS.md` define para evidencia
en general).

## Uso

```python
from src.gates.l4_evidence import FinancialGateEvidence, EvidenceStatus, evaluate_l4

evidence = FinancialGateEvidence.from_mapping(payload_json)
result = evaluate_l4(evidence, expected_cutoff="2026-09-26T23:59:00-03:00")

result.gate_result  # "PASS" | "FAIL_CLOSED"
result.l4_pass      # bool
result.reasons      # tuple[str, ...] — vacío solo si gate_result == "PASS"
```

`FinancialGateEvidence.from_mapping()` ignora silenciosamente strings de
estado desconocidos (los deja en `None`, que nunca es `CONFIRMED`) en lugar de
lanzar una excepción — así un payload externo malformado sigue cayendo del
lado fail-closed.

## Referencia de corte controlada

La referencia operativa vigente es `2026-09-26T23:59:00-03:00` (hora
Paraguay). No se cambia automáticamente: si `evaluate_l4()` recibe
`expected_cutoff` y `evidence.cutoff` no coincide exactamente, el gate falla
con una razón explícita.

## Bloqueos externos conocidos (a la fecha de este documento)

- CxC sin maestro homogéneo al corte.
- CxP sin reporte general homogéneo.
- Itaú sin movimientos 22–26/09.
- Continental: el septiembre disponible corresponde a 2025, no 2026.
- Cheques pendientes de confirmación.

Mientras estos bloqueos persistan, `evaluate_l4()` devolverá `FAIL_CLOSED` con
razones específicas por campo — este es el comportamiento correcto, no un
defecto a corregir con código.

## Relación con `src.financial_governance.FinancialGate`

Ese módulo (Sprint 004) es un gate **distinto y más liviano**: solo evita que
CRM/alertas/scoring conviertan saldos provisionales en acciones de cobranza o
riesgo. No autoriza escritura productiva ni cutover. `src/gates/l4_evidence.py`
es el gate formal para esas decisiones de mayor impacto. Ambos coexisten
intencionalmente.
