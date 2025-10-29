from functools import lru_cache
from colorama import Fore
import logging

logging.basicConfig(level=logging.INFO)

from app.core.logger import logger
from app.core.utils import get_environment_variable
from app.services.models import Source, SourceType

MAX_DAYS = int(get_environment_variable("MAX_DAYS", "10"))

__all__ = [
    "register_fetchers",
    "fetch_articles",
    "get_rss_urls",
    "get_subs_reddit_urls",
    "get_bluesky_urls",
]


def register_fetchers():
    from app.services.factory_fetcher import FetcherFactory
    from app.services.fetchers.reedit_fetcher import RedditFetcher
    from app.services.fetchers.rss_fetcher import RSSFetcher
    from app.services.fetchers.bluesky_fetcher import BlueskyFetcher
    from app.services.models import SourceType

    FetcherFactory.register_fetcher(SourceType.RSS, RSSFetcher)
    FetcherFactory.register_fetcher(SourceType.REDDIT, RedditFetcher)
    FetcherFactory.register_fetcher(SourceType.BLUESKY, BlueskyFetcher)


def get_rss_urls():
    """
    Obtient la liste des URL RSS à traiter à partir des variables d'environnement.
    Le .env ne contient que des types string et au format JSON
    """
    from app.read_opml import parse_opml_to_rss_list
    from app.services.models import Source, SourceType

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


def fetch_articles(fetcher, sources_urls):
    all_articles = []
    for source in sources_urls:
        try:
            articles = fetcher.fetch_articles(source, max_days=MAX_DAYS)
            all_articles.extend(articles)
            logger.info(
                f"{len(articles)} articles récents de {source.name or source.url}"
            )
        except Exception as e:
            logger.error(f"Error fetching from {source.url}: {e}")
    return all_articles


@lru_cache(maxsize=1)
def _load_json_reddit_bluesky(config_path):
    import json
    logger.info(Fore.LIGHTMAGENTA_EX + f"Chargement du fichier de configuration : {config_path}")
    with open(config_path, "r") as f:
        return json.load(f)


# def load_sources_from_config(config_path: str, type_source: SourceType) -> list[Source]:
def _load_sources_from_config(config_path: str, type_source: str) -> list[Source]:
    """
    Support pour un fichier JSON qui peut inclure Reddit et Bluesky
    Exemple de structure :
    REDDIT
    {
        "sources": [
            {
                "type": "reddit",
                "subreddit": "MachineLearning",
                "name": "ML Reddit",
                "sort_by": "hot",
                "time_filter": "day"
            },
    }
    BLUESKY
    {
        "sources": [
            {
                "type": "bluesky",
                "url": "@user.bsky.social",
                "name": "Tech Expert"
            },
        ]
    }
    """

    config = _load_json_reddit_bluesky(config_path)

    logger.info(Fore.LIGHTRED_EX + f"filter sources Reddit ou Bluesky : {type_source}")
    sources = []
    for source_config in config.get("sources", []):
        if type_source == "reddit":
            sources.append(
                Source(
                    type=SourceType.REDDIT,
                    url=f"reddit.com/r/{source_config['subreddit']}",
                    name=source_config.get("name"),
                    subreddit=source_config["subreddit"],
                    sort_by=source_config.get("sort_by", "hot"),
                    time_filter=source_config.get("time_filter", "day"),
                )
            )
        if type_source == "bluesky":
            sources.append(
                Source(
                    type=SourceType.BLUESKY,
                    url=source_config["url"],
                    name=source_config.get("name"),
                )
            )

    return sources


def get_subs_reddit_urls():
    """
    Obtient la liste des URL Reddit à traiter à partir du fichier myreddit.json
    """
    MY_REDDIT_FILE = get_environment_variable("REDDIT_FILE",None)
    if not MY_REDDIT_FILE:
        logger.warning("Aucun fichier Reddit spécifié.")
        raise ValueError("Aucun fichier Reddit spécifié.")
    return _load_sources_from_config(MY_REDDIT_FILE, SourceType.REDDIT.value)
    # return _load_sources_from_config(MY_REDDIT_FILE, "reddit")


def get_bluesky_urls():
    """
    Obtient la liste des URL Bluesky à traiter à partir du fichier mybluesky.json
    """
    BLUESKY_FILE = get_environment_variable("BLUESKY_FILE", None)
    if not BLUESKY_FILE:
        logger.warning("Aucun fichier Bluesky spécifié.")
        raise ValueError("Aucun fichier Bluesky spécifié.")

    return _load_sources_from_config(BLUESKY_FILE, SourceType.BLUESKY.value)
