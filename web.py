# Interface minimaliste pour lire les articles résumés sur une page web
# uvicorn web:app --reload # http://127.0.0.1:8000/ 
#
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

app = FastAPI()
app.mount("/static", StaticFiles(directory="templates/web"), name="static")
templates = Jinja2Templates(directory="templates/web")

#
# Filtres pour les templates jinja2 
# champ | filtre
# 
def format_date(value):
    """filtre jinga2 pour formatage de la date en FR"""
    if isinstance(value, str):
        date_obj = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        return date_obj.strftime("%d/%m/%Y")
    return value.strftime("%d/%m/%Y")

def format_local_datetime(utc_datetime, tz: str = "Europe/Paris"):
    """filtre de conversion UTC -> heure Paris"""
    from datetime import datetime, timezone
    import pytz
    if not utc_datetime:
        return "N/A"
    # Convertit UTC → Europe/Paris
    local_tz = pytz.timezone(tz)
    local_datetime = utc_datetime.replace(tzinfo=timezone.utc).astimezone(local_tz)
    return local_datetime.strftime('%d/%m/%Y à %H:%M')


# Ajoute les filtres à l'environnement Jinja2 de FastAPI pour utilisation champ | filtre
templates.env.filters["format_date"] = format_date
templates.env.filters["format_local_datetime"] = format_local_datetime

@app.get("/")
def read_articles(request: Request, date: str = None):
    """Affiche les articles filtrés par date de publication."""
    from db import read_articles
    articles = read_articles(date)
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles}
    )