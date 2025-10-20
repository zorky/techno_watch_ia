from functools import lru_cache
from services.factory_fetcher import FetcherFactory
from services.models import Source, SourceType, UnifiedState
from core.logger import logger
from colorama import Fore 
import time
from core.utils import get_environment_variable
from .utils_fetch_nodes import fetch_articles, get_rss_urls, register_fetchers, get_bluesky_urls, get_subs_reddit_urls

import logging
logging.basicConfig(level=logging.INFO)

MAX_DAYS = int(get_environment_variable("MAX_DAYS", "10"))

def fetch_rss_node(state: UnifiedState) -> dict:   
    """fetch des flux RSS"""    
    start = time.time()
    logger.info(f"🔵 RSS fetch START at {start}")

    fetcher_rss = FetcherFactory.create_fetcher(SourceType.RSS)        
    sources_urls = get_rss_urls()
    all_articles = fetch_articles(fetcher_rss, sources_urls)    
    
    logger.info(Fore.CYAN + f"fetch_rss_node : {len(all_articles)} articles RSS :")   

    logger.info(Fore.WHITE + f"🔵 RSS fetch END after {time.time() - start:.2f}s")

    return {"rss_articles": all_articles}

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
    start = time.time()
    logger.info(f"🔵 REDDIT fetch START at {start}")

    sources_url = get_subs_reddit_urls()
    logger.info(Fore.LIGHTCYAN_EX + f"sources Reddit : {sources_url}")
    all_articles = fetch_articles(fetcher_reddit, sources_url)    
    
    logger.info(Fore.CYAN + f"fetch_reddit_node : {len(all_articles)} articles Reddit :")  
    logger.info(Fore.WHITE + f"🔵 REDDIT fetch END after {time.time() - start:.2f}s")

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
    start = time.time()
    logger.info(f"🔵 BLUESKY fetch START at {start}")

    sources_url = get_bluesky_urls()
    logger.info(Fore.LIGHTGREEN_EX + f"sources Reddit : {sources_url}")
    all_articles = fetch_articles(fetcher_bluesky, sources_url)    
    
    logger.info(Fore.CYAN + f"fetcher_bluesky_node : {len(all_articles)} articles Bluesky :")  
    
    logger.info(Fore.WHITE + f"🔵 BLUESKY fetch END after {time.time() - start:.2f}s")

    # state.model_copy n'est pas possible sans quelques hack dans un graphe en //
    return {"bluesky_articles": all_articles}

def dispatch_node(state: UnifiedState) -> UnifiedState:
    """dispatcher vers les noeuds fetchers"""
    register_fetchers()
    return state

def merge_fetched_articles(state: UnifiedState) -> dict:
    """Noeud de fusion des données ramenés par les fetchers"""
    """Fusionne tous les articles des différentes sources"""    
    from collections import Counter
    from core.logger import print_color

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
    
    source_counts = Counter(item['source'].value for item in all_articles)
    color = Fore.LIGHTWHITE_EX
    print_color(color, "=" * 60)
    print_color(color, f"merge_fetched_articles {source_counts}")
    print_color(color, "=" * 60)

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
    
