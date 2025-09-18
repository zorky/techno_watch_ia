from pydantic import BaseModel

class ArticleModel(BaseModel):
    """Modèle Pydantic de vérification"""
    title: str
    link: str
    summary: str
    score: str # # ou float/int ?
    published: str

    # class Config:
    #     from_attributes = True  # Utile utilisation ORM mode plus tard