"""Configuración central. Zona horaria, corte y registro de fuentes.
Sólo se listan URLs entregadas por el mandante; las demás quedan 'POR_LOCALIZAR'
(no se inventan direcciones)."""
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/Asuncion")
HORA_CORTE = (5, 20)
ESCUDO = RAIZ / "assets" / "escudo_ejercito_original.jpg"
PALETA = {"verde": "#06291F", "negro": "#080B0A", "dorado": "#D8AC42",
          "blanco": "#FFFFFF", "rojo": "#C62828", "amarillo": "#FFD600"}

ESTACIONES_PARAGUAY = ["Bahía Negra", "Fuerte Olimpo", "Vallemí", "Concepción", "Rosario",
                       "Puerto Antequera", "Asunción", "Itá Enramada", "Villeta", "Alberdi",
                       "Humaitá", "Pilar"]
PUNTOS_PARANA = ["Ciudad del Este", "Itaipú", "Ayolas", "Yacyretá", "Encarnación"]
PAISES = ["Brasil", "Argentina", "Bolivia", "Chile", "Uruguay"]

# id -> (institución, url|None, método de acceso previsto)
FUENTES = {
    "DMH":   ("DMH/DINAC Paraguay", "https://www.meteorologia.gov.py/", "HTML; parser pendiente"),
    "CPC":   ("NOAA/CPC ENSO Advisory", "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/", "HTML/texto 'ENSO Diagnostic Discussion'; parser pendiente"),
    "OMM":   ("Organización Meteorológica Mundial", "https://wmo.int/", "HTML; parser pendiente"),
    "EBY":   ("Entidad Binacional Yacyretá", "https://www.eby.gov.py/", "HTML; parser pendiente"),
    "ITAIPU":("Itaipú Binacional", "https://www.itaipu.gov.py/", "HTML; parser pendiente"),
    "SEN":   ("Secretaría de Emergencia Nacional", "https://www.sen.gov.py/", "HTML; parser pendiente"),
    "COE":   ("COE Ayolas (complementaria, no primaria)", "https://coe.ordium.fun/", "HTML; contrastar con EBY/SEN"),
    "MADES": ("MADES", "https://www.mades.gov.py/", "HTML"),
    "INFONA":("INFONA", "https://www.infona.gov.py/", "HTML"),
    "INE":   ("INE", "https://www.ine.gov.py/", "HTML"),
    "PNA":   ("Prefectura General Naval", None, "POR_LOCALIZAR: canal oficial no verificado"),
    "ARMADA":("Armada Paraguaya", None, "POR_LOCALIZAR: canal oficial no verificado"),
    "SATSEN":("SAT-SEN", None, "POR_LOCALIZAR: portal vigente no verificado"),
}
