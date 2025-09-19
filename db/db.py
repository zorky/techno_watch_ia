import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy import DDL
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

class ArticleFTS(Base):
    __tablename__ = 'articles_fts'
    # __table_args__ = {'sqlite_autoincrement': True}
    __table_args__ = (
        {'sqlite_autoincrement': True},
        # Index('idx_fts_title', 'title', unique=True),  # Empêche les doublons
        # Configuration minimale pour FTS5 (obligatoire)
        # {'prefixes': ['title', 'content']}  # Active la recherche par préfixe
    )

    rowid = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(String)

    # Création de la table FTS5 via DDL : nécessite l'event create_fts_table
    _fts_create = DDL("""
    CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
        title, content,
        tokenize='unicode61',
        prefix='2,3'
    )
    """)

    @classmethod
    def search(cls, session, query):
        return session.execute(text(f"""
            SELECT * FROM {cls.__tablename__}
            WHERE content MATCH :query
        """), {'query': query}).fetchall()

# nécessaire si la table est créée par SQL : CREATE VIRTUAL dans le modèle ArticleFTS
@event.listens_for(ArticleFTS.__table__, 'after_create')
def create_fts_table(target, connection, **kw):
    connection.execute(ArticleFTS._fts_create)

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

def _save_to_fts(summaries: list[dict]):
    """
    Sauvegarde les articles en base FTS5 pour la recherche plein texte.

    Args:
        summaries: Liste des articles résumés à insérer
    """
    with get_db() as session:
        try:
            # Filtre les articles déjà existants
            existing_fts = session.query(ArticleFTS.title).all()
            existing_titles = {title for (title,) in existing_fts}

            # Prépare les nouveaux articles FTS (ceux pas encore indexés)
            new_fts_articles = [
                {"title": item["title"], "content": item["summary"]}
                for item in summaries
                if item["title"] not in existing_titles
            ]

            if new_fts_articles:
                logger.info(f"Indexation FTS de {len(new_fts_articles)} nouveaux articles")
                session.bulk_insert_mappings(ArticleFTS, new_fts_articles)
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'indexation FTS: {str(e)}")
            raise e
        
    # for item in summaries:
    #     with engine.connect() as conn:
    #         conn.execute(
    #             text(f"INSERT INTO {ArticleFTS.__tablename__} (title, content) VALUES (:title, :content)"),
    #             {"title": item["title"], "content": item["summary"]}
    #         )
    #         conn.commit()


def save_to_db(summaries: list[dict]):
    """
    Sauvegarde les articles en base avec validation Pydantic avec insertion en bulk.
    Les articles n'ayant pas déjà été insérés le sont : filtre sur titre et date

    Args:
        summaries: Liste de articles à insérer

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
                _save_to_fts(new_articles)  # Indexe les nouveaux articles en FTS      
        except Exception as e:
            session.rollback()
            raise e            

if __name__ == "__main__":
    init_db()
    articles = read_articles()
    _save_to_fts(articles)
    print(f"Nombre d'articles en base: {len(articles)}")