from functools import lru_cache
from services.factory_fetcher import FetcherFactory
from services.models import Source, SourceType, UnifiedState
from core.logger import logger
from colorama import Fore 
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

def _fetch_articles(fetcher, sources_urls):
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

def fetch_rss_node(state: UnifiedState) -> dict:   
    """fetch des flux RSS"""    
    fetcher_rss = FetcherFactory.create_fetcher(SourceType.RSS)        
    sources_urls = _get_rss_urls()
    all_articles = _fetch_articles(fetcher_rss, sources_urls)    
    
    logger.info(Fore.CYAN + f"fetch_rss_node : {len(all_articles)} articles RSS :")    
    
    return {"rss_articles": all_articles}

@lru_cache(maxsize=1)
def _load_json_reddit_bluesky(config_path):
    import json
    
    with open(config_path, 'r') as f:
        return json.load(f)    

# def _load_sources_from_config(config_path: str, type_source: SourceType) -> list[Source]:
def _load_sources_from_config(config_path: str, type_source: str) -> list[Source]:
    """
    Support pour un fichier JSON qui peut inclure Reddit et Bluesky
    Exemple de structure :
    {
        "sources": [            
            {
                "type": "reddit",
                "subreddit": "MachineLearning",
                "name": "ML Reddit",
                "sort_by": "hot",
                "time_filter": "day"
            },
            {
                "type": "bluesky",
                "url": "@user.bsky.social",
                "name": "Tech Expert"
            },            
        ]
    }
    """
    
    config = _load_json_reddit_bluesky(config_path)

    logger.info(Fore.LIGHTRED_EX + f"Source pour {type_source}")
    sources = []
    for source_config in config.get('sources', []):
        logger.info(Fore.RED + f"filter sources Reddit ou Bluesky {source_config['type']} {type_source} : {source_config['type'] == type_source}")
                     
        if source_config['type'] == type_source:
            # logger.info(f"Oui c'est REDDIT {source_config['type'] == type_source}")   
            sources.append(Source(
                type=SourceType.REDDIT,
                url=f"reddit.com/r/{source_config['subreddit']}",
                name=source_config.get('name'),
                subreddit=source_config['subreddit'],
                sort_by=source_config.get('sort_by', 'hot'),
                time_filter=source_config.get('time_filter', 'day')
            ))        
        elif source_config['type'] == type_source:
            logger.info(f"Oui c'est BLUESKY {source_config['type'] == type_source}")
            sources.append(Source(
                type=SourceType.BLUESKY,
                url=source_config['url'],
                name=source_config.get('name')
            ))        
    
    return sources

def _get_subs_reddit_urls():
    """
    Obtient la liste des URL Reddit à traiter à partir du fichier myreddit.json
    """    
    MY_REDDIT_FILE = get_environment_variable("REDDIT_FILE", "myreddit.json")    
    # return _load_sources_from_config(MY_REDDIT_FILE, SourceType.REDDIT.value)
    return _load_sources_from_config(MY_REDDIT_FILE, "reddit")

def _get_bluesky_urls():
    """
    Obtient la liste des URL Bluesky à traiter à partir du fichier myreddit.json
    """    
    MY_REDDIT_FILE = get_environment_variable("REDDIT_FILE", "myreddit.json")    
    return _load_sources_from_config(MY_REDDIT_FILE, "bluesky")
    # return _load_sources_from_config(MY_REDDIT_FILE, SourceType.BLUESKY.value)

def fetch_reddit_node(state: UnifiedState) -> dict:
    """fetch des canaux Reddit"""
    REDDIT_CLIENT_ID = get_environment_variable('REDDIT_CLIENT_ID', None)
    REDDIT_CLIENT_SECRET = get_environment_variable('REDDIT_CLIENT_SECRET', None)

    fetcher_reddit = FetcherFactory.create_fetcher(
            SourceType.REDDIT,
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="TechnoWatch 1.0"
    )
    sources_url = _get_subs_reddit_urls()
    logger.info(Fore.LIGHTCYAN_EX + f"sources Reddit : {sources_url}")
    all_articles = _fetch_articles(fetcher_reddit, sources_url)    
    
    logger.info(Fore.CYAN + f"fetch_reddit_node : {len(all_articles)} articles Reddit :")  

    # state.model_copy n'est pas possible sans quelques hack dans un graphe en //
    return {"reddit_articles": all_articles}

def fetch_bluesky_node(state: UnifiedState) -> dict:
    BLUESKY_HANDLE = get_environment_variable("BLUESKY_HANDLE", "your_bluesky_handle.bsky.social")
    BLUESKY_PASSWORD = get_environment_variable("BLUESKY_PASSWORD", "app_password")

    fetcher_bluesky = FetcherFactory.create_fetcher(
            SourceType.BLUESKY,
            handle=BLUESKY_HANDLE,
            password=BLUESKY_PASSWORD
    )    
    sources_url = _get_bluesky_urls()
    logger.info(Fore.LIGHTGREEN_EX + f"sources Reddit : {sources_url}")
    all_articles = _fetch_articles(fetcher_bluesky, sources_url)    
    
    logger.info(Fore.CYAN + f"fetcher_bluesky_node : {len(all_articles)} articles Bluesky :")  

    # state.model_copy n'est pas possible sans quelques hack dans un graphe en //
    return {"bluesky_articles": all_articles}

def dispatch_node(state: UnifiedState) -> UnifiedState:
    """dispatcher vers les noeuds fetchers"""
    _register_fetchers()
    return state

def merge_fetched_articles(state: UnifiedState) -> dict:
    """Noeud de fusion des données ramenés par les fetchers"""
    """Fusionne tous les articles des différentes sources"""    
    all_articles = []
    
    # Récupère de chaque source
    all_articles.extend(state.rss_articles or [])
    all_articles.extend(state.reddit_articles or [])
    all_articles.extend(state.bluesky_articles or [])
    
    if state.rss_articles:
        logger.info(f"Clés d'un article RSS : {list(state.rss_articles[0].keys())}")
    if state.reddit_articles:
        logger.info(f"Clés d'un article Reddit : {list(state.reddit_articles[0].keys())}")
    if state.bluesky_articles:
        logger.info(f"Clés d'un article Bluesky : {list(state.bluesky_articles[0].keys())}")

    # Déduplique si nécessaire
    # seen_urls = set()
    # unique_articles = []
    # for article in all_articles:
    #     url = article.get("url")
    #     if url and url not in seen_urls:
    #         seen_urls.add(url)
    #         unique_articles.append(article)

    # logger.info(f"merge des articles : {unique_articles}")
    # return state.model_copy(update={"articles": unique_articles})    
    logger.info(f"merge des articles : {len(all_articles)}")
    return state.model_copy(update={"articles": all_articles}) 
    

# def unified_fetch_node(state: UnifiedState) -> UnifiedState:    
#     _register_fetchers()

#     REDDIT_CLIENT_ID = get_environment_variable('REDDIT_CLIENT_ID', None)
#     REDDIT_CLIENT_SECRET = get_environment_variable('REDDIT_CLIENT_SECRET', None)

#     BLUESKY_HANDLE = get_environment_variable("BLUESKY_HANDLE", "your_bluesky_handle.bsky.social")
#     BLUESKY_PASSWORD = get_environment_variable("BLUESKY_PASSWORD", "app_password")

#     all_articles = []

#     # Configuration des fetchers
#     fetchers = {
#         SourceType.RSS: FetcherFactory.create_fetcher(SourceType.RSS),
#         SourceType.REDDIT: FetcherFactory.create_fetcher(
#             SourceType.REDDIT,
#             client_id=REDDIT_CLIENT_ID,
#             client_secret=REDDIT_CLIENT_SECRET,
#             user_agent="TechnoWatch 1.0"
#         ),
#         SourceType.BLUESKY: FetcherFactory.create_fetcher(
#             SourceType.BLUESKY,
#             handle=BLUESKY_HANDLE,
#             password=BLUESKY_PASSWORD
#         )
#     }

#     for source in state.sources:
#         try:
#             fetcher = fetchers.get(source.type)
#             if fetcher:
#                 articles = fetcher.fetch_articles(source, max_days=MAX_DAYS)
#                 all_articles.extend(articles)
#                 logger.info(
#                     f"{len(articles)} articles récents de {source.name or source.url}"
#                 )
#         except Exception as e:
#             logger.error(f"Error fetching from {source.url}: {e}")

#     return UnifiedState(
#         sources=state.sources,
#         keywords=state.keywords,
#         articles=all_articles,
#         filtered_articles=state.filtered_articles,
#         summaries=state.summaries,
#     )