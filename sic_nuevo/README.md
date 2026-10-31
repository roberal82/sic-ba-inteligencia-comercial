# SIC nuevo

Implementacion independiente (solo libreria estandar, Python 3.11+) de las funciones de inteligencia comercial
descritas en el analisis. No usa ni modifica `src/`, `ia/` ni `app.py` del proyecto original.

- `sicnuevo/parsers/`: un adaptador por reporte (cobros, pagos, cheques). **Los formatos son supuestos
  documentados en cada modulo**; ajustarlos al export real y probarlos con fixtures anonimizados.
- `sicnuevo/store.py`: SQLite, carga idempotente por clave natural, moneda como parte de la clave.
- `reglas.toml`: umbrales y pesos; cada alerta y score registra `version_reglas`.
- `sicnuevo/alertas.py`, `scoring.py`: reglas puras, montos por moneda (sin mezclar PYG/USD).

```
python -m unittest discover -s tests
python -m sicnuevo.cli reporte_cobros.txt reporte_pagos.txt --db sic.db
```

Pendiente: dashboards (leer de SQLite), autenticacion, forecast con modelo estacional, asistente sobre vistas SQL.
