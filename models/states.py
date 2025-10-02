from pydantic import BaseModel
from typing import Optional

# =========================
# Définition de l’état langgraph
# =========================

class RSSState(BaseModel):
    rss_urls: list[str]
    keywords: list[str]
    articles: Optional[list[dict]] = None # dict Article : 'title', 'summary', 'link', 'published', 'score', 'source'
    filtered_articles: Optional[list[dict]] = None # dict Article : 'title', 'summary', 'link', 'published', 'score', 'source'
    summaries: Optional[list[dict]] = None