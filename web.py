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
    """filtre jinga2 pour formatage de la date en FR"""
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

def _init_session():
    from sqlalchemy import create_engine, Column, Integer, String, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    Base = declarative_base()
    engine = create_engine(f'sqlite:///{DB_PATH}')
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    return session

def read_articles_sqlalchemy(date: str = None):
    from models.articles_db import Article
    session = _init_session()
    if date:
        articles = session.query(Article).filter(Article.date.like(f"%{date}%")).all()
    else:
        articles = session.query(Article).order_by(Article.date.desc()).all()
    return articles

def read_articles_raw(date: str = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if date:
        cursor.execute("SELECT * FROM articles WHERE date LIKE ?", (f"%{date}%",))
    else:
        cursor.execute("SELECT * FROM articles ORDER BY date DESC")
    articles = cursor.fetchall()
    conn.close()
    return articles

@app.get("/")
def read_articles(request: Request, date: str = None):
    """Affiche les articles filtrés par date de publication."""
    
    # articles = read_articles_raw(date)
    articles = read_articles_sqlalchemy(date)
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles}
    )