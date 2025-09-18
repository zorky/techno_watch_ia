# Interface minimaliste pour lire les articles résumés sur une page web
# uvicorn web:app --reload # http://127.0.0.1:8000/ 
#
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv
from jinja_filters import register_jinja_filters

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

app = FastAPI()
app.mount("/static", StaticFiles(directory="templates/web"), name="static")
templates = Jinja2Templates(directory="templates/web")

register_jinja_filters(templates.env)

@app.get("/")
def read_articles(request: Request, date: str = None):
    """Affiche les articles filtrés par date de publication."""
    from db import read_articles
    articles = read_articles(date)
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles}
    )