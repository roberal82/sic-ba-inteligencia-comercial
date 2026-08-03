# Radar Regional de Mercados — versión operativa

Aplicación web FastAPI para integrar mercados de Brasil, Paraguay y Argentina, eventos geopolíticos georreferenciados, gráficos y análisis de escenarios.

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir: http://localhost:8000

## Estructura

- `app/main.py`: backend FastAPI.
- `app/templates/index.html`: panel web.
- `.env.example`: claves de proveedores.
- `requirements.txt`: dependencias.

## Integraciones previstas

- Paraguay: Banco Central del Paraguay y Bolsa de Valores de Asunción.
- Brasil: Banco Central do Brasil y B3.
- Argentina: BCRA y BYMA.
- Internacional: proveedor de mercados globales.
- Geopolítica: GDELT y fuentes oficiales RSS.

## Advertencia

El panel incluye datos de demostración hasta que se conecten las APIs reales. No constituye asesoramiento financiero.
