"""Paraguay: el Banco Central del Paraguay y la BVPASA no publican una API JSON abierta y
documentada al momento de esta implementacion (solo portales web/paneles). Por lo tanto,
todos los indicadores de Paraguay se sirven como datos demostrativos, marcados como tal,
hasta que se habilite scraping autorizado, un convenio de datos o un proveedor de terceros.

Esta limitacion se documenta explicitamente en docs/DATA_SOURCES.md.
"""
from app.services import fallback_service

PENDING_NOTE = "Fuente sin API publica documentada (pendiente convenio BCP / BVPASA)"


async def get_indicators() -> list[dict]:
    return [
        {**i, "source": PENDING_NOTE, "data_status": "demo"}
        for i in fallback_service.demo_indicators()
        if i["country"] == "paraguay"
    ]
