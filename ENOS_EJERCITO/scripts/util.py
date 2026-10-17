import json, logging, datetime as dt
from .config import RAIZ, TZ, HORA_CORTE

def ahora(): return dt.datetime.now(TZ)

def corte(fecha: dt.date) -> dt.datetime:
    return dt.datetime(fecha.year, fecha.month, fecha.day, *HORA_CORTE, tzinfo=TZ)

def logger(nombre="enos"):
    (RAIZ / "logs").mkdir(exist_ok=True)
    lg = logging.getLogger(nombre)
    if not lg.handlers:
        lg.setLevel(logging.INFO)
        fh = logging.FileHandler(RAIZ / "logs" / "enos.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        lg.addHandler(fh); lg.addHandler(logging.StreamHandler())
    return lg

def cargar(p, defecto=None):
    try: return json.loads(open(p, encoding="utf-8").read())
    except FileNotFoundError: return defecto

def guardar(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    open(p, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=2))
