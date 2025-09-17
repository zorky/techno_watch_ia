from sqlalchemy import create_engine, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import sqlite3
import os
from dotenv import load_dotenv
from models.article import Article, ArticleModel

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

#
# Configuration SQL Alchemy
# 
Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
# Fonctions utilitaires DB
# 
@contextmanager
def get_db():
    """Générateur de session SQLAlchemy avec gestion automatique pour le close()."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def read_articles(date: str = None):
    """Lit les articles résumés qui ont été retenus pour la veille techno"""
    from db.db import session
    from models.article import Article    
    if date:
        articles = session.query(Article).filter(Article.date.like(f"%{date}%")).all()
    else:
        articles = session.query(Article).order_by(Article.date.desc()).all()
    return articles

def save_to_db(summaries: list[dict]):
    """
    Sauvegarde les articles en base avec validation Pydantic avec insertion en bulk.

    Args:
        summaries: Liste de dictionnaires contenant les articles à insérer

    Raises:
        ValueError: Si la validation Pydantic échoue
        Exception: Pour les erreurs de base de données
    """
    # from sqlalchemy.orm import sessionmaker
    # SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # session = SessionLocal()
    with get_db() as session:        
        try:
            for item in summaries:
                # existing_article = session.query(Article).filter_by(title=item["title"]).first()
                existing_article = session.query(Article).filter(and_(
                            Article.title == item["title"],
                            Article.date == item["published"])).first()                
                if not existing_article:
                    article = Article(
                        title=item["title"],
                        link=item["link"],
                        summary=item["summary"],
                        score=item["score"],
                        date=item["published"]
                    )
                    session.add(article)
            session.commit()

            # validation Pydantic
            # """
            # pydantic_core._pydantic_core.ValidationError: 1 validation error for ArticleModel
            # date
            # Field required [type=missing, input_value={'title': 'DjangoCon US\x...: '2025-09-07T22:00:00'}, input_type=dict]
            #     For further information visit https://errors.pydantic.dev/2.11/v/missing

            # """
            # validated_articles = [ArticleModel(**item) for item in summaries]
            # articles_data = [
            #     article.model_dump() for article in validated_articles
            # ]
            # session.bulk_insert_mappings(Article, articles_data)
            # session.commit()
            ## session.bulk_insert_mappings(Article, [
            ##     article.model_dump() for article in validated_articles
            ## ])
            # session.bulk_insert_mappings(Article, [{
            #     "title": item["title"],
            #     "link": item["link"],
            #     "summary": item["summary"],
            #     "score": item["score"],
            #     "date": item["published"]
            # } for item in summaries])
            # session.commit()
        except Exception as e:
            session.rollback()
            raise e            

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
