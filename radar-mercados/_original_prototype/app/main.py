from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import datetime as dt

app = FastAPI(title='Radar Regional de Mercados', version='1.0.0')
BASE = Path(__file__).resolve().parent
app.mount('/static', StaticFiles(directory=BASE/'static'), name='static')

@app.get('/', response_class=HTMLResponse)
def home():
    return (BASE/'templates'/'index.html').read_text(encoding='utf-8')

@app.get('/api/health')
def health():
    return {'status':'ok','time':dt.datetime.utcnow().isoformat()+'Z'}

@app.get('/api/dashboard')
def dashboard():
    # Base operativa preparada para sustituir estos datos por conectores oficiales.
    return {
        'mode':'operational-template',
        'updated_at':dt.datetime.utcnow().isoformat()+'Z',
        'sources':{
            'paraguay':['Banco Central del Paraguay','Bolsa de Valores de Asunción'],
            'brasil':['Banco Central do Brasil','B3'],
            'argentina':['BCRA','BYMA'],
            'geopolitics':['GDELT','RSS oficiales']
        }
    }
