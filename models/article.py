from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime

Base = declarative_base()

class Article(Base):
    """Modèle entité BDD"""
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    dt_created = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    dt_updated = Column(DateTime, onupdate=func.now())
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    score = Column(String, nullable=False)
    published = Column(String, nullable=False, index=True)    

class ArticleModel(BaseModel):
    """Modèle Pydantic de vérification"""
    title: str
    link: str
    summary: str
    score: str # # ou float/int ?
    published: str

    # class Config:
    #     from_attributes = True  # Utile utilisation ORM mode plus tard