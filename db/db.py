import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from sqlalchemy import Enum as SQLAlchemyEnum
from contextlib import contextmanager
from dotenv import load_dotenv
from datetime import datetime, timezone
from models.article import ArticleModel
from services.models import SourceType

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
    source = Column(
        SQLAlchemyEnum(SourceType),
        nullable=False,
        default=SourceType.RSS,  # Optionnel : valeur par défaut
        index=True  # Optionnel : index pour les requêtes
    )

# Evènement pour màj de dt_updated - /!\ après la déclaration du modèle
@event.listens_for(Article, 'before_update')
def update_timestamp(mapper, connection, target):    
    target.dt_updated = datetime.now(timezone.utc)

class ArticleFTS:
    """Modèle pour la table FTS5 Full Text Search"""
    __tablename__ = 'articles_fts'

    @classmethod
    def execute_statement(cls, conn, statement):
        conn.execute(statement)
        conn.commit()

    @classmethod
    def create_trigger_if_not_exists(cls, conn, trigger_name, trigger_sql):
        # Vérifier si le trigger existe déjà
        result = conn.execute(text(f"""
            SELECT name FROM sqlite_master
            WHERE type='trigger' AND name='{trigger_name}'
        """)).fetchone()

        if not result:
            conn.execute(text(trigger_sql))
            conn.commit()

    @classmethod
    def init_table(cls, engine):                
        """Crée la table FTS5 manuellement."""
        triggers = {
            "sync_article_fts": f"""
                CREATE TRIGGER sync_article_fts AFTER INSERT ON {Article.__tablename__}
                BEGIN
                    INSERT INTO {cls.__tablename__}(article_id, title, content)
                    VALUES (new.id, new.title, new.summary);
                END;
            """,
            "sync_article_update": f"""
                CREATE TRIGGER sync_article_update AFTER UPDATE ON {Article.__tablename__}
                BEGIN
                    UPDATE {cls.__tablename__}
                    SET title = new.title, content = new.summary
                    WHERE article_id = new.id;
                END;
            """,
            "sync_article_delete": f"""
                CREATE TRIGGER sync_article_delete AFTER DELETE ON {Article.__tablename__}
                BEGIN
                    DELETE FROM {cls.__tablename__} WHERE article_id = old.id;
                END;
            """
        }        
        
        with engine.connect() as conn:        
            cls.execute_statement(conn, text(f"""                
                CREATE VIRTUAL TABLE IF NOT EXISTS {cls.__tablename__} USING fts5(
                    article_id,
                    title,
                    content,                    
                    tokenize='unicode61',
                    prefix='2,3'
                );                                               
                """))
            for name, sql in triggers.items():
                cls.create_trigger_if_not_exists(conn, name, sql)            

    @classmethod
    def insert(cls, session, title, content, published):
        logger.info(f"Insertion article dans FTS: {title}")
        session.execute(
            text(f"""
            INSERT OR IGNORE INTO {cls.__tablename__} (title, content, published)
            VALUES (:title, :content, :published)
            """),
            {'title': title, 'content': content, 'published': published}
        )

    @classmethod
    def bulk_insert(cls, session, articles):
        """Insère plusieurs articles en une requête."""
        logger.info(f"Insertion en bulk de {len(articles)} articles dans FTS")
        session.execute(
            text(f"""
            INSERT OR IGNORE INTO {cls.__tablename__} (title, content, published)
            VALUES (:title, :content, :published)
            """),
            articles  # Liste de dicts [{'title': '...', 'content': '...', 'published': '...'}, ...]
        )

    @classmethod
    def search(cls, session, query, date_min=None, date_max=None, limit=10):
        """
        Recherche plein texte dans les articles avec filtre optionnel par date.
        avec score basé sur rank().

        Args:
            session: Session SQLAlchemy
            query: Terme de recherche plein texte
            date_min: Date minimale (format YYYY-MM-DD, optionnel)
            date_max: Date maximale (format YYYY-MM-DD, optionnel)
            limit: Nombre maximum de résultats

        Returns:
            Liste des articles correspondant aux critères
        """
        # Les indices des 2 champs hightlights de la table articles_fts
        IDX_TITLE_TABLE = 1
        IDX_CONTENT_TABLE = 2        
        
        # Base SQL pour le CTE
        base_sql = f"""
            WITH ranked AS (
                SELECT                     
                    rowid, 
                    article_id,
                    highlight({cls.__tablename__}, {IDX_TITLE_TABLE}, '<mark>', '</mark>') AS title,
                    highlight({cls.__tablename__}, {IDX_CONTENT_TABLE}, '<mark>', '</mark>') AS content,                
                    -rank AS score
                FROM {cls.__tablename__}
                WHERE {cls.__tablename__} MATCH :query
        """

        # Ajout des filtres optionnels
        where_clauses = []
        params = {"query": query, "limit": limit}

        if date_min:
            where_clauses.append("a.published >= :date_min")
            params["date_min"] = date_min
        if date_max:
            where_clauses.append("a.published <= :date_max")
            params["date_max"] = date_max

        base_sql += f"""
            )
            SELECT 
                ranked.title as title, 
                ranked.content as content,  
                a.link as link,
                a.published as published,                                                
                ROUND(100.0 * ranked.score / (SELECT MAX(ranked.score) FROM ranked), 2) AS rank,
                a.source as source
            FROM ranked
            JOIN {Article.__tablename__} a on a.id = ranked.article_id
        """
        
        if where_clauses:
            base_sql += "    WHERE " + " AND ".join(where_clauses)
            logger.info(f"where {base_sql}")

        base_sql += f"""
            ORDER BY rank DESC
            LIMIT :limit
        """

        logger.info(f"SQL exécuté: {base_sql} avec {params}")
        # results = session.execute(text(base_sql), params).fetchall()
        results = session.execute(text(base_sql), params)
        results_as_dict = results.mappings().all()
        logger.info(f"results : {results_as_dict}")
        return results_as_dict
        # return results.fetchall()

    @classmethod
    def search_with_bm25(cls, session, query, date_min=None, date_max=None, limit=10):
        """
        Recherche plein texte dans les articles avec filtre optionnel par date,
        avec score basé sur bm25() : on opérationnel
        /!\ erreur :
        sqlite3.OperationalError: unable to use function bm25 in the requested context
        requête SQL générée :
        WITH ranked AS ( SELECT rowid, highlight(articles_fts, 0, '<mark>', '</mark>') AS title, highlight(articles_fts, 1, '<mark>', '</mark>') AS content, published, bm25(articles_fts) AS score FROM articles_fts WHERE articles_fts MATCH ? ) SELECT rowid, title, content, published, ROUND( 100.0 * ( (SELECT MAX(score) FROM ranked) - score ) / NULLIF((SELECT MAX(score) FROM ranked) - (SELECT MIN(score) FROM ranked), 0), 2 ) AS rank FROM ranked ORDER BY rank DESC LIMIT ?
        """

        base_sql = f"""
            WITH ranked AS (
                SELECT 
                    rowid, 
                    highlight({cls.__tablename__}, 0, '<mark>', '</mark>') AS title,
                    highlight({cls.__tablename__}, 1, '<mark>', '</mark>') AS content,
                    published,
                    bm25({cls.__tablename__}) AS score
                FROM {cls.__tablename__}
                WHERE {cls.__tablename__} MATCH :query
        """

        # Filtres optionnels
        where_clauses = []
        params = {"query": query, "limit": limit}

        if date_min:
            where_clauses.append("published >= :date_min")
            params["date_min"] = date_min
        if date_max:
            where_clauses.append("published <= :date_max")
            params["date_max"] = date_max

        if where_clauses:
            base_sql += " AND " + " AND ".join(where_clauses)

        # Normalisation : plus le score est faible, plus la pertinence est forte
        base_sql += """
            )
            SELECT 
                rowid, 
                title, 
                content, 
                published,
                ROUND(
                    100.0 * ( (SELECT MAX(score) FROM ranked) - score ) 
                    / NULLIF((SELECT MAX(score) FROM ranked) - (SELECT MIN(score) FROM ranked), 0), 
                    2
                ) AS rank
            FROM ranked
            ORDER BY rank DESC
            LIMIT :limit
        """

        logger.debug(f"SQL exécuté: {base_sql} avec {params}")
        return session.execute(text(base_sql), params).fetchall()

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
    ArticleFTS.init_table(engine)
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
    logger.info(f"Articles validés pour insertion: {articles_data}")
    return articles_data

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
        except Exception as e:
            session.rollback()
            raise e            

def search_fts(keywords: str):
    with get_db() as session:
        # Recherche plein texte seulement
        result1 = ArticleFTS.search(session, keywords or "intelligence artificielle")
        logger.info(f"Résultats FTS: {result1}")

        # Recherche avec filtre date
        result2 = ArticleFTS.search(
            session,
            "cybersécurité",
            date_min="2025-01-01",
            date_max="2025-12-31"
        )
        logger.info(f"Résultats FTS: {result2}")

        # Recherche depuis une date
        result3 = ArticleFTS.search(session, keywords or "docker", date_min="2025-09-01")
        logger.info(f"Résultats FTS: {result3}")

if __name__ == "__main__":    
    articles = read_articles()    
    print(f"Nombre d'articles en base: {len(articles)}")