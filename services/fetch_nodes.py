from services.models import SourceType, UnifiedState
from services.factory_fetcher import FetcherFactory

# from pydantic import BaseModel
# from typing import Optional, Union
# from enum import Enum

# class SourceType(str, Enum):
#     RSS = "rss"
#     REDDIT = "reddit"
#     # Futures sources
#     BLUESKY = "bluesky"
#     LINKEDIN = "linkedin"

# class Source(BaseModel):
#     type: SourceType
#     url: str
#     name: Optional[str] = None
#     # Paramètres spécifiques Reddit
#     subreddit: Optional[str] = None
#     sort_by: Optional[str] = "hot"  # hot, new, top, rising
#     time_filter: Optional[str] = "day"  # hour, day, week, month

# class UnifiedState(BaseModel):
#     sources: list[Source]  # Remplace rss_urls
#     keywords: list[str]
#     articles: Optional[list[dict]] = None
#     filtered_articles: Optional[list[dict]] = None
#     summaries: Optional[list[dict]] = None

async def unified_fetch_node(state: UnifiedState) -> UnifiedState:
    all_articles = []
    
    # Configuration des fetchers
    fetchers = {
        SourceType.RSS: FetcherFactory.create_fetcher(SourceType.RSS),
        SourceType.REDDIT: FetcherFactory.create_fetcher(
            SourceType.REDDIT,
            client_id="your_reddit_client_id",
            client_secret="your_reddit_client_secret",
            user_agent="your_app_name v1.0"
        )
    }
    
    for source in state.sources:
        try:
            fetcher = fetchers.get(source.type)
            if fetcher:
                articles = await fetcher.fetch_articles(source, max_days=7)
                all_articles.extend(articles)
                print(f"Fetched {len(articles)} articles from {source.name or source.url}")
        except Exception as e:
            print(f"Error fetching from {source.url}: {e}")
    
    return UnifiedState(
        sources=state.sources,
        keywords=state.keywords,
        articles=all_articles,
        filtered_articles=state.filtered_articles,
        summaries=state.summaries
    )