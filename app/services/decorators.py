from typing import Callable

import logging

logging.basicConfig(level=logging.INFO)
from app.core.logger import logger
from colorama import Fore

_FETCHERS = {}
_PIPELINE_NODES = []

# ============================================
# DÉCORATEUR DE CLASSE (Alternative)
# ============================================


def fetcher_class(cls):
    """
    Décorateur optionnel pour enregistrer une classe fetcher.

    Usage (si vous préférez):
        @fetcher_class
        class RSSFetcher(BaseFetcher):
            source_type = "rss"
            env_flag = "RSS_FETCH"
            ...
    """
    from app.services.factory_fetcher import FetcherRegistry

    logger.info(
        Fore.YELLOW + f"🏷️  Décorateur @fetcher_class appelé pour: {cls.__name__}"
    )
    FetcherRegistry.register(cls)
    logger.info(Fore.GREEN + f"✓ {cls.__name__} enregistré via décorateur")
    return cls


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
        _PIPELINE_NODES.append(
            {
                "name": node_name,
                "func": func,
                "needs_wrapper": needs_legacy_wrapper,
            }
        )
        return func

    return decorator
