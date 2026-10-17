# ENOS_EJERCITO — Sistema de reportes hidrometeorológicos

Pipeline: `colectar` → (carga de registros verificados) → `validar` → `generar` → `auditar`.

## Uso
    python3 -m scripts.diario        # ciclo completo, hora local America/Asuncion
    ./scripts/programar.sh           # muestra la línea de cron (NO la instala)

## Datos
Los valores NO se simulan. Cada registro verificado se carga en `datos/validados/AAAA-MM-DD.json`
con: institucion, titulo, url, fecha_publicacion, hora_publicacion (opcional), fecha_medicion, localidad,
indicador, valor, unidad, tipo (observado|pronostico|historico|no_confirmado),
estado (VERIFICADO|PARCIALMENTE VERIFICADO|NO VERIFICADO), bloque
(enos|regional|meteo|paraguay|parana|embalses|humanitario).
`validar.py` rechaza lo incompleto, lo posterior al corte (05:20 HOP) y lo NO VERIFICADO.

## Estado de implementación (honesto)
- Recolección con reintentos y registro de errores: implementada y ejecutada.
- Parsers por institución: PENDIENTES (requieren acceso a las fuentes para construirlos y probarlos).
- Fuentes sin URL verificada (no se inventan): Prefectura Naval, Armada, SAT-SEN.
- Escudo: falta `assets/escudo_ejercito_original.jpg`; la infografía reserva el espacio y lo advierte.
- Programador de tareas: NO activado ni comprobado.
