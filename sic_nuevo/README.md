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
python -m sicnuevo.dashboard --db sic.db --port 8000   # http://127.0.0.1:8000
```

`dashboard.py`: pagina de solo lectura (conexion SQLite `mode=ro`, escucha solo en 127.0.0.1) con KPIs por moneda,
antiguedad de cartera, mayores deudores, semaforo de liquidez a 30 dias y alertas. En la liquidez, los cobros
vencidos cuentan como cobrables dentro de los 30 dias y el saldo bancario se asume 0 (supuestos a revisar).

Pendiente: autenticacion (obligatoria antes de exponer el dashboard en red), forecast con modelo estacional, asistente sobre vistas SQL.
