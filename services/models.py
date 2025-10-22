from pydantic import BaseModel
from typing import Optional, Annotated
from operator import add
from enum import Enum

class SourceType(str, Enum):
    RSS = "rss"
    REDDIT = "reddit"
    BLUESKY = "bluesky"
    # Futures potentielles sources    
    # LINKEDIN = "linkedin"
    # TWITTER = "twitter"

class Source(BaseModel):
    type: SourceType
    url: str
    link: Optional[str] = None  # lien Web associé
    name: Optional[str] = None
    # Paramètres spécifiques Reddit
    subreddit: Optional[str] = None
    sort_by: Optional[str] = "hot"  # hot, new, top, rising
    time_filter: Optional[str] = "day"  # hour, day, week, month

def merge_dicts(left: dict, right: dict) -> dict:
    """fonction reducer pour Annotated, appelé par LangGraph"""
    return {**left, **right}

# class UnifiedState(TypedDict, total=False):
class UnifiedState(BaseModel):
    # Ces champs sont modifiés en parallèle -> nécessitent Annotated
    sources: Annotated[list, add] = []    

    # keywords: list[str] = []
    keywords: list[str]
 
    # Articles par source (modifiés en parallèle)
    rss_articles: Annotated[Optional[list[dict]], add] = None
    reddit_articles: Annotated[Optional[list[dict]], add] = None
    bluesky_articles: Annotated[Optional[list[dict]], add] = None

    articles: Optional[list[dict]] = None
    filtered_articles: Optional[list[dict]] = None
    summaries: Optional[list[dict]] = None

    