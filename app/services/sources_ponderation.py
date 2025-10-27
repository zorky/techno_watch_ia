from math import ceil
import logging
from app.services.models import SourceType

logging.basicConfig(level=logging.INFO)

from app.core.logger import logger, Fore
from app.core import get_environment_variable
from app.core.logger import print_color
from app.core.logger import count_by_type_articles


def _calculate_quotas(total_count):
    """Calcul des quotas par source selon % donnés en .env"""
    rss_min = ceil(
        total_count * float(get_environment_variable("RSS_WEIGHT", 50)) / 100
    )
    reddit_min = ceil(
        total_count * float(get_environment_variable("REDDIT_WEIGHT", 30)) / 100
    )
    bluesky_min = ceil(
        total_count * float(get_environment_variable("BLUESKY_WEIGHT", 20)) / 100
    )

    guaranteed_total = rss_min + reddit_min + bluesky_min
    remaining_slots = max(0, total_count - guaranteed_total)

    return {
        "rss_min": rss_min,
        "reddit_min": reddit_min,
        "bluesky_min": bluesky_min,
        "flexible": remaining_slots,
    }


def _apply_freshness_adjustment(articles_by_source: list[dict], quotas: dict) -> dict:
    """Ajustement selon la fraîcheur des RSS"""

    total_articles_sources = len(articles_by_source)
    articles_rss = list(
        filter(lambda x: x["source"] == SourceType.RSS, articles_by_source)
    )
    recent_rss_ratio = len(articles_rss) / max(1, total_articles_sources)
    logger.info(
        Fore.YELLOW
        + f"Ratio RSS récents : {recent_rss_ratio:.2f} ({len(articles_rss)}/{total_articles_sources})"
    )

    threshold = float(get_environment_variable("FRESHNESS_BOOST_THRESHOLD", 0.3))

    if recent_rss_ratio < threshold:
        # Peu de RSS récents → redistribuer vers autres sources
        boost_slots = quotas["rss_min"] // 3
        quotas["rss_min"] -= boost_slots
        quotas["flexible"] += boost_slots

    return quotas


def _fill_flexible_slots(remaining_articles, flexible_slots, processed_sources: list):
    """Répartir les slots flexibles avec pondération"""
    WEIGHTS = {"rss": 1.5, "reddit": 1.0, "bluesky": 1.2}
    logger.info(Fore.CYAN + f"{processed_sources}")
    # Mélanger et trier par score pondéré
    weighted_articles = []
    for source, articles in remaining_articles.items():
        if source in processed_sources:
            for article in articles:
                # logger.info(Fore.GREEN + f" {type(article)} {article.keys()}")
                logger.info(Fore.GREEN + f"{article['score']}")
                weighted_score = float(article["score"]) * WEIGHTS[source]
                weighted_articles.append((weighted_score, article))

    weighted_articles.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in weighted_articles[:flexible_slots]]


def _count_by_type_articles(title, articles):
    from collections import Counter

    source_counts = Counter(item["source"].value for item in articles)
    color = Fore.LIGHTYELLOW_EX
    print_color(color, "=" * 60)
    print_color(color, f"{title} {source_counts}")
    print_color(color, "=" * 60)


def select_articles_for_summary(articles_by_source: list[dict]) -> list[dict]:
    """
    Fonction principale qui orchestre la sélection des articles

    Args:
        articles_by_source: ['title', 'summary', 'link', 'published', 'score', 'source']
        (old : {'rss': [...], 'reddit': [...], 'bluesky': [...]})

    Returns:
        Liste des articles sélectionnés et équilibrés
    """
    count_by_type_articles(
        f"Nombre d'articles sources {len(articles_by_source)}", articles_by_source
    )

    limit_articles_to_resume = int(
        get_environment_variable("LIMIT_ARTICLES_TO_RESUME", 15)
    )

    # ÉTAPE 1: Calculer les quotas de base (Phase 1)
    quotas = _calculate_quotas(limit_articles_to_resume)
    # Résultat: {'rss_min': 6, 'reddit_min': 3, 'bluesky_min': 2, 'flexible': 4}
    logger.info(Fore.CYAN + f"Quotas initiaux: {quotas}")

    # ÉTAPE 2: Ajuster selon la fraîcheur des RSS (Phase 4)
    quotas = _apply_freshness_adjustment(articles_by_source, quotas)
    # Peut modifier les quotas si RSS peu actifs
    logger.info(Fore.MAGENTA + f"Quotas après ajustement fraîcheur: {quotas}")

    # ÉTAPE 3: Sélectionner les articles garantis par quota
    selected_articles = []
    remaining_articles = {}

    processed_sources = []
    for source in SourceType:
        logger.info(
            Fore.RED
            + f"Traitement source {source.value} avec quota {quotas.get(f'{source.value}_min', 0)}"
        )
        # articles = articles_by_source[source]
        articles = list(filter(lambda x: x["source"] == source, articles_by_source))

        count_by_type_articles(
            f"{len(articles)} articles disponibles pour la source {source.value}",
            articles,
        )

        # logger.info(Fore.BLUE + f" - {len(articles)} articles disponibles pour la source {source.value}")
        if not articles:
            continue

        quota_key = f"{source.value}_min"
        quota = quotas.get(quota_key, 0)

        # Trier par score de pertinence (supposant que c'est déjà fait)
        selected = articles[:quota]
        selected_articles.extend(selected)

        # Garder le reste pour la phase flexible
        remaining_articles[source] = articles[quota:]
        processed_sources.append(source)

    # ÉTAPE 4: Remplir les slots flexibles (Phase 2) : TOTO : à corriger selon si fetcher activé ou non
    if quotas["flexible"] > 0 and processed_sources:
        flexible_articles = _fill_flexible_slots(
            remaining_articles, quotas["flexible"], processed_sources
        )
        selected_articles.extend(flexible_articles)

    logger.info(Fore.RED + f"selected_articles {len(selected_articles)}")
    _count_by_type_articles("Nombre d'articles sélectionnés", selected_articles)

    limit_selected = selected_articles[:limit_articles_to_resume]
    logger.info(Fore.RED + f"limit_selected {len(limit_selected)}")
    _count_by_type_articles(
        f"Nombre d'articles sélectionnés limite à {limit_articles_to_resume}",
        limit_selected,
    )

    return limit_selected
