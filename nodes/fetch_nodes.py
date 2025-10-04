import os

from dotenv import load_dotenv
from services.factory_fetcher import FetcherFactory
from services.models import SourceType, UnifiedState
from core.logger import logger

import logging
logging.basicConfig(level=logging.INFO)


load_dotenv()

MAX_DAYS = int(os.getenv("MAX_DAYS", "10"))

def _register_fetchers():
    from services.factory_fetcher import FetcherFactory
    from services.reedit_fetcher import RedditFetcher
    from services.rss_fetcher import RSSFetcher
    from services.bluesky_fetcher import BlueskyFetcher
    from services.models import SourceType

    FetcherFactory.register_fetcher(SourceType.RSS, RSSFetcher)
    FetcherFactory.register_fetcher(SourceType.REDDIT, RedditFetcher)
    FetcherFactory.register_fetcher(SourceType.BLUESKY, BlueskyFetcher)

def unified_fetch_node(state: UnifiedState) -> UnifiedState:
    _register_fetchers()

    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', None)
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', None)

    BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE", "your_bluesky_handle.bsky.social")
    BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD", "app_password")

    all_articles = []

    # Configuration des fetchers
    fetchers = {
        SourceType.RSS: FetcherFactory.create_fetcher(SourceType.RSS),
        SourceType.REDDIT: FetcherFactory.create_fetcher(
            SourceType.REDDIT,
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="TechnoWatch 1.0"
        ),
        SourceType.BLUESKY: FetcherFactory.create_fetcher(
            SourceType.BLUESKY,
            handle=BLUESKY_HANDLE,
            password=BLUESKY_PASSWORD
        )
    }

    for source in state.sources:
        try:
            fetcher = fetchers.get(source.type)
            if fetcher:
                articles = fetcher.fetch_articles(source, max_days=MAX_DAYS)
                all_articles.extend(articles)
                logger.info(
                    f"{len(articles)} articles récents de {source.name or source.url}"
                )
        except Exception as e:
            logger.error(f"Error fetching from {source.url}: {e}")

    return UnifiedState(
        sources=state.sources,
        keywords=state.keywords,
        articles=all_articles,
        filtered_articles=state.filtered_articles,
        summaries=state.summaries,
    )