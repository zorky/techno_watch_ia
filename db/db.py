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

class ArticleFTS:
    """Modèle pour la table FTS5 Full Text Search"""
    __tablename__ = 'articles_fts'
    @classmethod
    def init_table(cls, engine):
        """Crée la table FTS5 manuellement."""
        with engine.connect() as conn:
            conn.execute(text(f"""
                -- DROP TABLE IF EXISTS articles_fts;
                CREATE VIRTUAL TABLE IF NOT EXISTS {cls.__tablename__} USING fts5(
                    title,
                    content,
                    published,
                    tokenize='unicode61',
                    prefix='2,3'
                );
            """))
            conn.commit()

    @classmethod
    def insert(cls, session, title, content, published):
        session.execute(
            text(f"""
            INSERT OR IGNORE INTO {cls.__tablename__} (title, content, published)
            VALUES (:title, :content, :published)
            """),
            {'title': title, 'content': content, 'published': published}
        )

    @classmethod
    def search(cls, session, query, date_min=None, date_max=None):
        """
        Recherche plein texte dans les articles avec filtre optionnel par date.

        Args:
            session: Session SQLAlchemy
            query: Terme de recherche plein texte
            date_min: Date minimale (format YYYY-MM-DD, optionnel)
            date_max: Date maximale (format YYYY-MM-DD, optionnel)

        Returns:
            Liste des articles correspondant aux critères
        """
        # Construction dynamique de la requête
        sql = f"SELECT rowid, title, content, published FROM {cls.__tablename__}"
        where_parts = []
        params = {}
        where_parts.append(f"{cls.__tablename__} MATCH :query")        
        params['query'] = query

        # Ajout des filtres date
        if date_min:
            where_parts.append("published >= :date_min")
            params['date_min'] = date_min
        if date_max:
            where_parts.append("published <= :date_max")
            params['date_max'] = date_max

        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        logger.info(f"Exécutant: {sql} avec {params}")
        return session.execute(text(sql), params).fetchall()


#
# Configuration SQL Alchemy
# 
SQLALCHEMY_DB = f'sqlite:///{DB_PATH}'
engine = create_engine(
    SQLALCHEMY_DB,
    connect_args={"check_same_thread": False},  # Nécessaire pour SQLite avec FastAPI et le multi-threads
    echo=True  # Affiche les requêtes SQL (optionnel, pour le debug))
)

def recreate_fts_table():
    """Supprime et recrée la table FTS5."""
    with engine.connect() as conn:
        # Supprimer l'ancienne table si elle existe
        conn.execute(text("DROP TABLE IF EXISTS articles_fts"))

        # Créer la nouvelle table
        ArticleFTS.__table__.create(bind=engine, checkfirst=True)

        # Vérifier la création
        result = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE name='articles_fts'"
        )).fetchone()
        logger.info(f"Table créée avec: {result[0] if result else 'Aucune table'}")

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
    return articles_data

def save_to_fts(summaries: list[dict]):
    """
    Sauvegarde les articles en base FTS5 pour la recherche plein texte.

    Args:
        summaries: Liste des articles résumés à insérer
    """
    if not summaries:
        return

    with get_db() as session:
        try:            
            logger.info(f"Indexation FTS de {len(summaries)} articles")
            # Préparation des données
            # fts_data = [
            #     {
            #         "title": item.title,
            #         "content": item.summary,
            #         "published": item.published
            #     }
            #     for item in summaries
            # ]
            for item in summaries:
                ArticleFTS.insert(
                    session,
                    title=item["title"],
                    content=item["summary"],
                    published=item["published"]
                )
            session.commit()

            # Insertion en bulk avec gestion des doublons via OR IGNORE
            # session.execute(
            #     text("""
            #     INSERT OR IGNORE INTO articles_fts (title, content, published)
            #     VALUES (:title, :content, :published)
            #     """),
            #     fts_data
            # )
            # logger.info(f"Indexation FTS de {fts_data} articles")
            # session.execute(
            #     text("""
            #     INSERT INTO articles_fts (title, content, published)
            #     VALUES (:title, :content, :published)
            #     """),
            #     fts_data
            # )
            inserted_count = session.execute(
                text("SELECT changes()")  # Compte le nombre de lignes effectivement insérées
            ).scalar()

            if inserted_count > 0:
                logger.info(f"Indexation FTS de {inserted_count} nouveaux articles")

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'indexation FTS: {str(e)}")
            raise e


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

                save_to_fts(new_articles)
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
    # init_db()
    articles = read_articles()
    save_to_fts(articles)
    print(f"Nombre d'articles en base: {len(articles)}")