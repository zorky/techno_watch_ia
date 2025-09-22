# Interface minimaliste pour lire les articles résumés sur une page web
# uvicorn web:app --reload # http://127.0.0.1:8000/ 
#
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request, Depends

from dotenv import load_dotenv
from jinja_filters import register_jinja_filters

from typing import Optional

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "techno-watch.db")

app = FastAPI()
app.mount("/static", StaticFiles(directory="templates/web"), name="static")
templates = Jinja2Templates(directory="templates/web")

register_jinja_filters(templates.env)

@app.get("/")
def read_articles(request: Request, date: str = None):
    """Affiche les articles filtrés par date de publication."""
    from db import read_articles
    articles = read_articles(date)
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "articles": articles}
    )

@app.get("/search")
def search_articles(
    request: Request,
    q: str,
    date_min: Optional[str] = None,
    date_max: Optional[str] = None,
    limit: int = 10,
    ajax: bool = False
    # session: Session = Depends(get_db)
):
    """
    Endpoint pour la recherche plein texte.
    Args:
        q: Terme de recherche
        date_min/date_max: Filtres de date (format YYYY-MM-DD)
        limit: Nombre max de résultats
    """
    from db.db import ArticleFTS, get_db
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
                "id": row.rowid,
                "title": row.title,
                # "title_highlight": row.title_highlight,  # Titre avec mots clés en gras
                "summary": row.content,
                # "published": row.published,                
                "score": row.rank
            }
            for row in results
        ]
    logger.info(f"Recherche '{q}' - {len(articles)} résultats")
    logger.info(f"Articles: {articles}")
    if ajax:
        # Retourne UNIQUEMENT le fragment HTML des résultats
        return templates.TemplateResponse(
            "fragments/_search_ajax_results.html",
            {"request": request, "articles": articles}
        )
    else:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "articles": articles}
        )