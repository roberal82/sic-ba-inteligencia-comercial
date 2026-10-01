# QA_REPORT — Sprint Multiagente 001 / ERP Drift Analysis

## RESULTADO

**PASS_WITH_WARNINGS**

El motor, después de las correcciones registradas en esta rama, supera la suite
funcional original y la ampliación adversarial usando únicamente workbooks
sintéticos. No se ejecutó contra BASE/CURRENT reales, no se accedió al ERP y no
se modificaron L4, L7, `main` ni producción.

La Fase B puede ejecutarse **solo contra COPIAS privadas** y bajo las condiciones
del apartado “Recomendación técnica”. Este resultado no autoriza producción.

## Evidencia de ejecución

- Rama revisada: `agent/codex-drift`.
- Checkpoint inicial revisado: `77b4f58` (`Sprint 001: implement synthetic ERP drift engine`).
- Suite original, antes de cambios: **96 PASS, 0 FAIL, 4 subtests PASS**.
- Primera corrida de la nueva suite adversarial contra el checkpoint: **10 PASS, 14 FAIL**.
- Tests adversariales agregados: **27** (26 en `tests/test_erp_diff_adversarial.py` y 1 de configuración).
- Suite final completa: **123 PASS, 0 FAIL, 4 subtests PASS**.
- Comando final: `.venv\Scripts\python.exe -m pytest -q`.
- Duración de la última corrida: 4,78 s.
- `git diff --check`: PASS (solo avisos esperados LF/CRLF de Git en Windows).
- Compilación: `python -m compileall -q src/erp_diff_engine tests`: PASS.
- Búsqueda estática de secretos/emails: cero coincidencias en el alcance del motor y tests.

## Matriz de validación solicitada

| # | Escenario | Resultado y evidencia |
|---:|---|---|
| 1 | Archivos idénticos | PASS — cero drift material en fixture normal con PK. |
| 2 | Hoja agregada | PASS — `SHEET_ADDED`. |
| 3 | Hoja eliminada | PASS — `SHEET_REMOVED`, clasificación `CRITICAL`. |
| 4 | Cambio de orden de hojas | PASS — `SHEET_ORDER_CHANGED`. |
| 5 | Columna agregada al final | PASS — `COLUMN_ADDED`. |
| 6 | Columna agregada en medio | PASS — detectada como `COLUMN_ADDED`, sin falso rename en el caso adversarial. |
| 7 | Columna eliminada | PASS — al final y en medio, sin falso rename en los casos probados. |
| 8 | Columna renombrada | PASS — rename 1:1 como `HEADER_CHANGED`. |
| 9 | Nombres de columnas duplicados | PASS con advertencia — ahora produce `DUPLICATE_HEADER` `CRITICAL` por cada fuente; el contenido de columnas duplicadas no se considera emparejable de forma única. |
| 10 | Fila agregada | PASS con PK; sin PK queda además marcada como heurística. |
| 11 | Fila eliminada | PASS con PK; sin PK queda además marcada como heurística. |
| 12 | Fila modificada | PASS — `VALUE_MODIFIED`. |
| 13 | Varias filas similares | PASS con advertencia — el caso adversarial genera `ROW_MATCH_AMBIGUOUS`. |
| 14 | Ausencia de primary key | PASS con advertencia — `SequenceMatcher` se declara `INSUFFICIENT_EVIDENCE`, nunca correspondencia documental. |
| 15 | Primary key configurada | PASS — matching exacto por clave. |
| 16 | Primary key duplicada | PASS — `DUPLICATE_KEY` `CRITICAL` en BASE/CURRENT. |
| 17 | Primary key nula | PASS — `NULL_IN_KEY` `CRITICAL`. |
| 18 | Filas reordenadas | PASS con PK: cero drift; sin PK: hallazgo explícito de ambigüedad. |
| 19 | Fórmulas modificadas | PASS — fórmula y valores cacheados se reportan por separado. |
| 20 | Fórmula distinta con mismo valor cacheado | PASS — `FORMULA_CHANGED_SAME_VALUE`, revisión humana. |
| 21 | Valor cacheado ausente | PASS con advertencia — `FORMULA_CACHE_MISSING` y `FORMULA_CHANGED_NO_CACHED_VALUE`; nunca se afirma igualdad calculada. |
| 22 | Libro vacío | PASS — workbook sintético con hoja predeterminada vacía. |
| 23 | Hoja vacía | PASS — encabezados sin filas y hoja completamente vacía. |
| 24 | Encabezados incompletos | PASS — cambio estructural y calidad de encabezado. |
| 25 | Encabezados vacíos | PASS con advertencia — `EMPTY_HEADER` `RISK` por fuente. |
| 26 | Fechas `dd/mm/yyyy` | PASS — normalización semántica y cambio de tipo visible. |
| 27 | Fechas Excel serial | PASS — serial con formato fecha se compara con texto `dd/mm/yyyy`. |
| 28 | Importes PYG | PASS — texto con separador de miles/prefijo y numérico. |
| 29 | Enteros vs floats | PASS con limitación — la normalización distingue tipos en memoria; Excel/openpyxl colapsa `7.0` integral a entero al serializar y ese origen no puede recuperarse. |
| 30 | `None` vs cadena vacía | PASS — equivalentes en comparación, sin falso cambio de valor. |
| 31 | Unicode y acentos | PASS — ida y vuelta UTF-8 en reportes. |
| 32 | Nombres de hojas especiales | PASS. |
| 33 | Archivos corruptos | PASS — error controlado `EngineInputError`, sin traceback crudo como contrato público. |
| 34 | Ruta inexistente | PASS — error controlado en API/CLI. |
| 35 | Path traversal | PASS — filenames y `log_file` con `..`/ruta absoluta fuera de output son rechazados. |
| 36 | Intento de escritura fuera de output | PASS — reportes y log quedan confinados a `output_dir`. |
| 37 | Output ya existente | PASS — reemplazo atómico, sin temporales residuales. |
| 38 | Doble ejecución | PASS. |
| 39 | Idempotencia | PASS — bytes idénticos para las cinco salidas obligatorias. |
| 40 | Reproducibilidad | PASS — mismas salidas con `PYTHONHASHSEED=1` y `777`. |
| 41 | SHA-256 de inputs | PASS — ambos hashes verificados contra cálculo independiente. |
| 42 | Inputs sin modificación | PASS — comparación byte a byte antes/después. |
| 43 | Clasificación de riesgo | PASS — defaults, sensibles, overrides y nuevos hallazgos cubiertos. |
| 44 | Diferencias sin regla explícita | PASS — no se marcan `EXPECTED`; se bloqueó `EXPECTED` vía `severity_overrides`. |
| 45 | Totales configurados | PASS — match/mismatch, columna ausente y valores inválidos/caché ausente. |
| 46 | Sin totales configurados | PASS — no se infieren ni ejecutan totales automáticamente. |

## Hallazgos CRITICAL

**2 encontrados, 2 corregidos, 0 pendientes sin mitigación.**

1. `log_file` aceptaba una ruta arbitraria y podía escribir fuera de
   `output_dir`. Se confinó a una ruta relativa segura dentro del output y se
   agregó prueba de traversal.
2. Una PK configurada pero inexistente lanzaba `KeyError`, el motor la absorbía
   por hoja y aun así emitía reportes con cero diferencias. Ahora falla cerrado
   con `EngineInputError` y no produce un resumen engañoso.

## Hallazgos HIGH

**7 encontrados; corrección o señalización explícita aplicada a los 7.**

1. Dos fórmulas sin caché (`None`/`None`) se clasificaban como “mismo valor
   calculado”. Se separaron fórmula, caché y estado de caché.
2. El orden de diferencias keyed dependía del hash seed de Python. Se añadió un
   orden estable para claves compuestas.
3. `severity_overrides` podía asignar `EXPECTED` sin `expected_rules`. Se
   rechaza tanto al cargar configuración como defensivamente al clasificar.
4. Encabezados duplicados quedaban ocultos por el mapa “primera aparición”. Se
   reportan como `DUPLICATE_HEADER` `CRITICAL`.
5. Una columna de total configurada pero inexistente quedaba solo como metadata,
   sin hallazgo. Ahora es `CONTROL_TOTAL_COLUMN_MISSING` `CRITICAL`.
6. Valores no numéricos en totales eran ignorados y podían producir un falso
   `0 == 0`. Ahora el total queda `INVALID_VALUES` y genera hallazgo `CRITICAL`.
7. El matching sin PK no exponía suficientemente su falta de evidencia. Ahora
   genera `ROW_MATCH_AMBIGUOUS` y `row_matching_evidence=INSUFFICIENT_EVIDENCE`
   cuando existe cambio heurístico.

## Hallazgos MEDIUM

**3 encontrados, 3 corregidos.**

1. Un ZIP/XLSX corrupto podía escapar como `BadZipFile`; ahora se normaliza a
   `EngineInputError`.
2. Encabezados vacíos no generaban hallazgo persistente si eran iguales en ambos
   libros; ahora se reportan como `EMPTY_HEADER`.
3. La suite usaba `xlsxwriter` y `pytest` sin declararlos; se agregaron a
   `requirements.txt` para reproducibilidad del QA.

## Hallazgos LOW

**1 limitación confirmada, pendiente por naturaleza del formato.**

- Excel/openpyxl no conserva necesariamente la distinción de origen entre un
  entero y un float integral (`7` frente a `7.0`). El motor puede reportar el
  cambio de tipo solo cuando el tipo sobrevive a la lectura.

## Correcciones realizadas

- Fail-closed para PK configurada ausente; se eliminó el `except Exception` que
  convertía errores de hoja en una ejecución aparentemente exitosa.
- Orden determinista de claves y prueba entre procesos con hash seeds distintos.
- Estado explícito de caché de fórmulas y cuatro columnas nuevas en
  `diff_formulas.csv`: valores cacheados BASE/CURRENT y estados BASE/CURRENT.
- Detección de encabezados duplicados/vacíos.
- Etiqueta de evidencia para matching keyed/posicional y hallazgo de ambigüedad.
- Confinamiento del log dentro de `output_dir`, contenido sin timestamps para
  reproducibilidad, handler por ejecución y cierre garantizado.
- Errores controlados para XLSX/ZIP corruptos.
- Validación estricta de `EXPECTED`: solo por `expected_rules` explícitas.
- Totales configurados fallan visiblemente ante columna ausente, valor inválido
  o fórmula sin caché.
- Dependencias de test declaradas.

## Limitaciones conocidas y riesgos pendientes

1. Sin PK, `SequenceMatcher` sigue siendo una heurística. El motor ahora lo
   declara, pero no puede confirmar identidad de filas.
2. openpyxl no calcula fórmulas. Un caché presente también puede estar obsoleto;
   el motor no puede certificar su frescura.
3. Con encabezados duplicados o vacíos, el motor alerta, pero no promete un diff
   completo de todas las columnas ambiguas. Esos hallazgos deben bloquear la
   interpretación automática.
4. Inserciones/renombres múltiples y simultáneos pueden seguir siendo ambiguos;
   el rename 1:1 y las inserciones simples probadas funcionan correctamente.
5. Los reportes contienen valores de celdas, nombres de hojas y rutas de input.
   Las salidas de Fase B son privadas y nunca deben versionarse ni publicarse.
6. La atomicidad es por archivo, no transaccional para el conjunto de cinco
   reportes; una interrupción extrema puede dejar una mezcla que debe regenerarse.
7. No se hizo prueba de volumen con copias grandes. Aunque openpyxl abre en modo
   lectura, el snapshot y las diferencias se mantienen en memoria.
8. El SHA-256 se calcula antes de cargar el workbook. Las copias deben mantenerse
   inmutables durante la ejecución para evitar una carrera externa.

## Seguridad

- Sin credenciales, tokens, claves privadas ni emails en código/tests revisados.
- Sin IDs internos, datos de clientes/proveedores ni fixtures reales.
- Sin llamadas de red, acceso a Drive, SQL o ERP productivo desde el motor.
- Inputs abiertos con `read_only=True`; no se invoca `save()` sobre ellos.
- Escrituras limitadas a output configurado y validado.
- Las únicas rutas privadas visibles en el repositorio son ejemplos e
  instrucciones públicas ya existentes (`private-data/...`), no datos reales.

## Archivos modificados

- `requirements.txt`
- `src/erp_diff_engine/classify.py`
- `src/erp_diff_engine/config.py`
- `src/erp_diff_engine/engine.py`
- `src/erp_diff_engine/formula_diff.py`
- `src/erp_diff_engine/loader.py`
- `src/erp_diff_engine/models.py`
- `src/erp_diff_engine/report.py`
- `src/erp_diff_engine/row_diff.py`
- `src/erp_diff_engine/structure_diff.py`
- `src/erp_diff_engine/totals.py`
- `tests/test_erp_diff_adversarial.py`
- `tests/test_erp_diff_config.py`
- `QA_REPORT.md`

## Recomendación técnica para Fase B

**Sí, Fase B puede ejecutarse contra COPIAS privadas BASE/CURRENT, con gate
PASS_WITH_WARNINGS y las siguientes condiciones obligatorias:**

1. Copias inmutables, nunca archivos del ERP productivo.
2. Inputs y outputs bajo `private-data/` o ruta externa ignorada, con acceso
   restringido; ningún reporte se agrega a Git.
3. `primary_keys` configuradas en toda hoja donde se pretenda confirmar
   correspondencia de filas. Sin PK, el resultado es candidato y requiere
   revisión humana.
4. `control_totals` y `sensitive_columns` declarados expresamente; el motor no
   los infiere.
5. Todo `DUPLICATE_HEADER`, `EMPTY_HEADER`, `DUPLICATE_KEY`, `NULL_IN_KEY`,
   `FORMULA_CACHE_MISSING`, total inválido o `ROW_MATCH_AMBIGUOUS` debe revisarse
   antes de aceptar conclusiones.
6. Verificar que las copias con fórmulas hayan sido guardadas por una aplicación
   que calcule y cachee resultados, sin asumir que un caché presente es fresco.
7. Ejecutar primero sobre una copia de tamaño representativo y vigilar memoria,
   espacio de salida y tiempo.
8. Comparar SHA-256 antes/después y conservar los inputs sin cambios durante la
   corrida.

**No se autoriza ejecución contra producción, escritura en ERP, cambio de L4/L7,
push ni merge a `main`. Se requiere revisión humana de este reporte.**
