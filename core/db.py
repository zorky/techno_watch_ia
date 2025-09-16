from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

#
# SQL Alchemy
# Configuration de la connexion
# 
Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()



def save_to_db(summaries: list[dict]):
    """Sauvegarde les résumés dans SQLite."""        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for item in summaries:
        cursor.execute(
            "INSERT INTO articles (title, link, summary, score, date) VALUES (?, ?, ?, ?, ?)",
            (item["title"], item["link"], item["summary"], item['scoring'], item["published"])
        )
    conn.commit()
    conn.close()

def init_db():
    """Initialise la base de données SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            summary TEXT NOT NULL,
            score TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
