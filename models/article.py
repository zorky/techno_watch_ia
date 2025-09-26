from pydantic import BaseModel

from services.models import SourceType

class ArticleModel(BaseModel):
    """Modèle Pydantic de vérification"""
    title: str
    link: str
    summary: str
    score: str # ou float/int ?
    published: str
    source: SourceType

    # class Config:
    #     from_attributes = True  # Utile utilisation ORM mode plus tard