from pydantic import BaseModel
from typing import Optional
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

class UnifiedState(BaseModel):
    sources: list[Source]  # Remplace rss_urls
    keywords: list[str]
    articles: Optional[list[dict]] = None
    filtered_articles: Optional[list[dict]] = None
    summaries: Optional[list[dict]] = None

    