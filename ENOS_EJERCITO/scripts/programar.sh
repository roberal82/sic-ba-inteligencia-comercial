#!/bin/sh
# Muestra (no instala) la entrada de cron. 05:20 America/Asuncion; verifique con: crontab -l y logs/enos.log
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
echo "CRON_TZ=America/Asuncion"
echo "20 5 * * * cd $RAIZ && python3 -m scripts.diario >> logs/cron.log 2>&1"
