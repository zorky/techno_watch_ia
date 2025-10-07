from services.factory_fetcher import FetcherFactory
from services.models import SourceType, UnifiedState
from core.logger import logger
from core.utils import get_environment_variable

import logging
logging.basicConfig(level=logging.INFO)

MAX_DAYS = int(get_environment_variable("MAX_DAYS", "10"))

def _register_fetchers():
    from services.factory_fetcher import FetcherFactory
    from services.fetchers.reedit_fetcher import RedditFetcher
    from services.fetchers.rss_fetcher import RSSFetcher
    from services.fetchers.bluesky_fetcher import BlueskyFetcher
    from services.models import SourceType

    FetcherFactory.register_fetcher(SourceType.RSS, RSSFetcher)
    FetcherFactory.register_fetcher(SourceType.REDDIT, RedditFetcher)
    FetcherFactory.register_fetcher(SourceType.BLUESKY, BlueskyFetcher)

def _get_rss_urls():
    """
    Obtient la liste des URL RSS à traiter à partir des variables d'environnement.
    Le .env ne contient que des types string et au format JSON
    """
    from read_opml import parse_opml_to_rss_list
    from services.models import Source, SourceType
    OPML_FILE = get_environment_variable("OPML_FILE", "my.opml")

    logger.info("Obtention des URL RSS à traiter...")
    rss_list_opml = parse_opml_to_rss_list(OPML_FILE)

    return [
        Source(
            type=SourceType.RSS, name=feed.titre, url=feed.lien_rss, link=feed.lien_web
        )
        for feed in rss_list_opml
        if (
            logger.debug(f"Flux RSS : {feed.titre} - {feed.lien_rss} - {feed.lien_web}")
            or True
        )
    ]

def fetch_rss_node(state: UnifiedState) -> UnifiedState:
    from services.fetchers.rss_fetcher import RSSFetcher
    fetcher_rss = FetcherFactory.create_fetcher(SourceType.RSS)    
    # fetcher_rss = fetchers.get(SourceType.RSS)
    sources_urls = _get_rss_urls()
    all_articles = []
    if fetcher_rss:
        for source in sources_urls:
            try:                
                articles = fetcher_rss.fetch_articles(source, max_days=MAX_DAYS)
                all_articles.extend(articles)
                logger.info(
                    f"{len(articles)} articles récents de {source.name or source.url}"
                )
            except Exception as e:
                logger.error(f"Error fetching from {source.url}: {e}")

    return {
        **state,
        "rss_articles": all_articles
    }

def fetch_reddit_node(state: UnifiedState) -> UnifiedState:
    REDDIT_CLIENT_ID = get_environment_variable('REDDIT_CLIENT_ID', None)
    REDDIT_CLIENT_SECRET = get_environment_variable('REDDIT_CLIENT_SECRET', None)

    FetcherFactory.create_fetcher(
            SourceType.REDDIT,
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="TechnoWatch 1.0"
    )

def fetch_bluesky_node(state: UnifiedState) -> UnifiedState:
    BLUESKY_HANDLE = get_environment_variable("BLUESKY_HANDLE", "your_bluesky_handle.bsky.social")
    BLUESKY_PASSWORD = get_environment_variable("BLUESKY_PASSWORD", "app_password")

    FetcherFactory.create_fetcher(
            SourceType.BLUESKY,
            handle=BLUESKY_HANDLE,
            password=BLUESKY_PASSWORD
    )


def dispatch_node(state: UnifiedState) -> UnifiedState:
    """dispatcher vers les noeuds fetchers"""
    _register_fetchers()
    return state

def merge_fetched_articles(state: UnifiedState) -> UnifiedState:
    """Noeud de fusion des données ramenés par les fetchers"""
    """Fusionne tous les articles des différentes sources"""
    all_articles = []
    
    # Récupère de chaque source
    all_articles.extend(state.get("rss_articles", []))
    all_articles.extend(state.get("reddit_articles", []))
    all_articles.extend(state.get("bluesky_articles", []))
    
    # Déduplique si nécessaire
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return {
        **state,
        "articles": unique_articles,
        "total_fetched": len(unique_articles)
    }

def unified_fetch_node(state: UnifiedState) -> UnifiedState:    
    _register_fetchers()

    REDDIT_CLIENT_ID = get_environment_variable('REDDIT_CLIENT_ID', None)
    REDDIT_CLIENT_SECRET = get_environment_variable('REDDIT_CLIENT_SECRET', None)

    BLUESKY_HANDLE = get_environment_variable("BLUESKY_HANDLE", "your_bluesky_handle.bsky.social")
    BLUESKY_PASSWORD = get_environment_variable("BLUESKY_PASSWORD", "app_password")

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