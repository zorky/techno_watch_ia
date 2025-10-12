from typing import Callable, Optional
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph

from typing import Dict, Type, Optional
import logging
logging.basicConfig(level=logging.INFO)
from colorama import Fore
from core.logger import logger
from services.fetchers.base_fetcher import BaseFetcher
from services.fetchers.rss_fetcher import RSSFetcher
# from services.fetchers.reedit_fetcher import RedditFetcher
# from services.fetchers.bluesky_fetcher import BlueskyFetcher

from factory_fetcher import FetcherRegistry

_FETCHERS = {}
_PIPELINE_NODES = []

def register_fetchers_auto():
    """Découvre automatiquement tous les BaseFetcher du module."""
    import inspect
    import sys
    
    logger.info(Fore.CYAN + f"name module {__name__}")
    
    # Récupère le module 'fetchers' ou adapte selon votre structure
    current_module = sys.modules[__name__]
    
    for name, obj in inspect.getmembers(current_module):
        if (inspect.isclass(obj) and 
            issubclass(obj, BaseFetcher) and 
            obj is not BaseFetcher):
            FetcherRegistry.register(obj)
    
    logger.info(f"✓ Auto-découverte: {FetcherRegistry.list_all()}")

# def register_fetchers_manual():
#     """À appeler une fois au démarrage de l'app."""
#     FetcherRegistry.register(RSSFetcher)
#     # FetcherRegistry.register(RedditFetcher)
#     # FetcherRegistry.register(BlueskyFetcher)
#     logger.info(f"Fetchers enregistrés: {FetcherRegistry.list_all()}")


# ============================================
# DÉCORATEUR DE CLASSE (Alternative)
# ============================================

def fetcher_class(fetcher_cls: Type[BaseFetcher]) -> Type[BaseFetcher]:
    """
    Décorateur optionnel pour enregistrer une classe fetcher.
    
    Usage (si vous préférez):
        @fetcher_class
        class RSSFetcher(BaseFetcher):
            source_type = "rss"
            env_flag = "RSS_FETCH"
            ...
    """
    return FetcherRegistry.register(fetcher_cls)

########################
# Décorateurs pour nous simplifier la vie
# Exemples d'usage :
#
# @fetcher("rss", "RSS_FETCH")
# def fetch_rss_node(state):
#     # votre code RSS
#     return state
#
# @pipeline_node("merge_articles")
# def merge_fetched_articles(state):
#     return state
########################

def fetcher(name: str, env_flag: str):
    """
    Décorateur pour enregistrer automatiquement un fetcher.
    
    Usage:
        @fetcher("rss", "RSS_FETCH")
        def fetch_rss_node(state):
            ...
    """
    def decorator(func: Callable):
        _FETCHERS[name] = {
            "func": func,
            "env_flag": env_flag,
            "node_name": f"fetch_{name}",
        }
        return func
    return decorator

def pipeline_node(node_name: str, needs_legacy_wrapper: bool = False):
    """
    Décorateur pour enregistrer un nœud du pipeline.
    
    Usage:
        @pipeline_node("filter")
        def filter_node(state):
            ...
    """
    def decorator(func: Callable):
        _PIPELINE_NODES.append({
            "name": node_name,
            "func": func,
            "needs_wrapper": needs_legacy_wrapper,
        })
        return func
    return decorator
