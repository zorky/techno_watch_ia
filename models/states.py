from pydantic import BaseModel
from typing import Optional

# =========================
# Définition de l’état langgraph
# =========================

class RSSState(BaseModel):
    rss_urls: list[str]
    keywords: list[str]
    articles: Optional[list[dict]] = None
    filtered_articles: Optional[list[dict]] = None
    summaries: Optional[list[dict]] = None