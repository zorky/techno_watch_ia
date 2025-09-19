import os
import logging
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from contextlib import contextmanager
from dotenv import load_dotenv
from models.article import ArticleModel
from datetime import datetime, timezone

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

# from core import logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()
#
# Modèles
# /!\ Après le declarative_base()
#
class Article(Base):
    """Modèle entité BDD"""
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    dt_created = Column(DateTime, 
                        server_default=func.now(),
                        default=lambda: datetime.now(timezone.utc),
                        nullable=False, 
                        index=True)
    dt_updated = Column(DateTime, 
                        onupdate=lambda: datetime.now(timezone.utc),  # Remplace utcnow()
                        default=lambda: datetime.now(timezone.utc),
                        nullable=False)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    score = Column(String, nullable=False)
    published = Column(String, nullable=False, index=True)    

# Evènement pour màj de dt_updated - /!\ après la déclaration du modèle
@event.listens_for(Article, 'before_update')
def update_timestamp(mapper, connection, target):    
    target.dt_updated = datetime.now(timezone.utc)

#
# Configuration SQL Alchemy
# 
SQLALCHEMY_DB = f'sqlite:///{DB_PATH}'
engine = create_engine(
    SQLALCHEMY_DB,
    connect_args={"check_same_thread": False},  # Nécessaire pour SQLite avec FastAPI et le multi-threads
    echo=True  # Affiche les requêtes SQL (optionnel, pour le debug))
)

def init_db():
    """Initialise la base de données SQLite."""
    Base.metadata.create_all(engine)
    print("Table 'articles' créée avec succès !")

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
    with get_db() as session:
        if date:
            articles = session.query(Article).filter(Article.published.like(f"%{date}%")).all()
        else:
            articles = session.query(Article).order_by(Article.published.desc()).all()
    return articles

def _validate_and_get_articles_summaries(summaries):
    validated_articles = [ArticleModel(**item) for item in summaries]
    articles_data = [
        article.model_dump() for article in validated_articles
    ]  
    return articles_data

def save_to_db(summaries: list[dict]):
    """
    Sauvegarde les articles en base avec validation Pydantic avec insertion en bulk.
    Les articles n'ayant pas déjà été insérés le sont : filtre sur titre et date

    Args:
        summaries: Liste de dictionnaires contenant les articles à insérer

    Raises:
        ValueError: Si la validation Pydantic échoue
        Exception: Pour les erreurs de base de données
    """    
    with get_db() as session:        
        try:            
            existing = session.query(Article.title, Article.published).all()
            existing_pairs = {(title, published) for title, published in existing}
            new_articles = [
                item for item in summaries
                if (item["title"], item["published"]) not in existing_pairs
            ]
            if new_articles:
                logger.info(f"Nombre de nouveaux articles {len(new_articles)}")            
                articles_data = _validate_and_get_articles_summaries(new_articles)  
                session.bulk_insert_mappings(Article, articles_data)
                session.commit()            
        except Exception as e:
            session.rollback()
            raise e            

