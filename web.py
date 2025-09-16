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

def format_date(value):
    """filtre jinga2 pour formatage de la date en FR"""
    if isinstance(value, str):
        date_obj = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        return date_obj.strftime("%d/%m/%Y")
    return value.strftime("%d/%m/%Y")

# Ajoute le filtre à l'environnement Jinja2 de FastAPI
templates.env.filters["format_date"] = format_date

@app.get("/")
def read_articles(request: Request, date: str = None):
    """Affiche les articles filtrés par date de publication."""
    from db import read_articles
    articles = read_articles(date)
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles}
    )