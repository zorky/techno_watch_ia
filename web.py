# Interface minimaliste pour lire les articles résumés sur une page web
# uvicorn web:app --reload # http://127.0.0.1:8000/ 
#
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

from dotenv import load_dotenv

from typing import Optional

import logging

from app.jinja_filters import register_jinja_filters
from app.services.models import SourceType
from app.db.db import ArticleFTS, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

TEMPLATES_WEB = "app/templates/web"

app = FastAPI()
app.mount("/static", StaticFiles(directory=TEMPLATES_WEB), name="static")
templates = Jinja2Templates(directory=TEMPLATES_WEB)

register_jinja_filters(templates.env)

@app.get("/")
async def read_articles(request: Request, date: str = None):
    """Affiche les articles filtrés par date de publication."""
    from app.db import read_articles
    articles = await read_articles(date) 
    logger.debug(f"Articles lus: len({articles})")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles}
    )

@app.get("/search")
async def search_articles(
    request: Request,
    q: str,
    date_min: Optional[str] = None,
    date_max: Optional[str] = None,
    limit: int = 10,
    ajax: bool = False    
):
    """
    Endpoint pour la recherche plein texte.
    Args:
        q: Terme de recherche
        date_min/date_max: Filtres de date (format YYYY-MM-DD)
        limit: Nombre max de résultats
    """
    
    from datetime import datetime    

    if not q:
        return {"error": "Le terme de recherche est obligatoire."}
    
    # Conversion des dates (optionnel, si vous voulez valider le format)
    try:
        if date_min:
            date_min = datetime.strptime(date_min, "%Y-%m-%d").date()
        if date_max:
            date_max = datetime.strptime(date_max, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Format de date invalide. Utilisez YYYY-MM-DD."}

    with get_db() as session:
        # Appel de la recherche FTS
        results = ArticleFTS.search(
            session=session,
            query=q,
            date_min=date_min,
            date_max=date_max,
            limit=limit
        )
        logger.debug(f"Résultats bruts: {results}")
        articles = [
            {                
                "title": row.title,
                "link": row.link,                
                "summary": row.content,
                "published": row.published,                
                "score": row.rank,
                "source": SourceType(row.source.lower()) if row.source else None,
            }
            for row in results
        ]
    logger.info(f"Recherche '{q}' - {len(articles)} résultats")    
    if ajax:        
        # Retourne uniquement le fragment HTML des résultats
        return templates.TemplateResponse(
            "fragments/_search_ajax_results.html",
            {"request": request, "articles": articles}
        )
    else:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "articles": articles}
        )