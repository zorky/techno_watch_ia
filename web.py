# Interface minimaliste pour lire les articles résumés sur une page web
# uvicorn web:app --reload # http://127.0.0.1:8000/ 
#
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

app = FastAPI()
app.mount("/static", StaticFiles(directory="templates/web"), name="static")
templates = Jinja2Templates(directory="templates/web")


def format_date(value):
    if isinstance(value, str):
        date_obj = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        return date_obj.strftime("%d/%m/%Y")
    return value.strftime("%d/%m/%Y")

# Ajoute le filtre à l'environnement Jinja2 de FastAPI
templates.env.filters["format_date"] = format_date

# Active le mode Row pour sqlite3
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.get("/")
def read_articles(request: Request, date: str = None):
    """Affiche les articles filtrés par date de publication."""
    # from core.db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if date:
        cursor.execute("SELECT * FROM articles WHERE date LIKE ?", (f"%{date}%",))
    else:
        cursor.execute("SELECT * FROM articles ORDER BY date DESC")
    articles = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles}
    )