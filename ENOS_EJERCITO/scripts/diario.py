"""Ejecución diaria completa: colectar -> generar -> auditar. Registra cada ejecución."""
import sys
from . import colectar, generar, auditar
from .util import logger, ahora

if __name__ == "__main__":
    lg = logger(); lg.info("INICIO ejecución diaria %s", ahora().isoformat())
    colectar.main(); generar.main(); rc = auditar.main()
    lg.info("FIN ejecución diaria rc=%s", rc); sys.exit(rc)
