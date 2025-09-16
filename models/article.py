from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    score = Column(String, nullable=False)
    date = Column(String, nullable=False)

class ArticleModel(BaseModel):
    title: str
    link: str
    summary: str
    score: str # # ou float/int ?
    date: str

    # class Config:
    #     from_attributes = True  # Utile utilisation ORM mode plus tard