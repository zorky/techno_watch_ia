import os
from math import ceil, floor
from dotenv import load_dotenv

load_dotenv()

def _calculate_quotas(total_count):
    """Calcul des quotas par source selon % donnés en .env"""
    rss_min = ceil(total_count * float(os.getenv('RSS_WEIGHT', 50)) / 100)
    reddit_min = ceil(total_count * float(os.getenv('REDDIT_WEIGHT', 30)) / 100)
    bluesky_min = ceil(total_count * float(os.getenv('BLUESKY_WEIGHT', 20)) / 100)

    guaranteed_total = rss_min + reddit_min + bluesky_min
    remaining_slots = max(0, total_count - guaranteed_total)
    
    return {
        'rss_min': rss_min,
        'reddit_min': reddit_min, 
        'bluesky_min': bluesky_min,
        'flexible': remaining_slots
    }

def _count_recent_rss(rss_articles):
    """
    Compte le nombre d'articles RSS publiés dans les MAX_DAYS derniers jours
    
    Returns:
        int: Nombre d'articles RSS récents
    """
    from datetime import datetime, timedelta
    max_days = int(os.getenv('MAX_DAYS', 5))
    cutoff_date = datetime.now() - timedelta(days=max_days)
    
    recent_count = 0
    for article in rss_articles:        
        article_date = article.get('published')        
        if article_date and article_date >= cutoff_date:
            recent_count += 1
    
    return recent_count

def _apply_freshness_adjustment(articles_by_source: list[dict], quotas: dict) -> dict:
    """Ajustement selon la fraîcheur des RSS"""
    total_rss = len(articles_by_source['rss'] or [])
    recent_rss_ratio = _count_recent_rss(articles_by_source['rss']) / max(1, total_rss)
    
    threshold = float(os.getenv('FRESHNESS_BOOST_THRESHOLD', 0.3))
    
    if recent_rss_ratio < threshold:
        # Peu de RSS récents → redistribuer vers autres sources
        boost_slots = quotas['rss_min'] // 3
        quotas['rss_min'] -= boost_slots
        quotas['flexible'] += boost_slots
        
    return quotas

def _fill_flexible_slots(remaining_articles, flexible_slots):
    """Répartir les slots flexibles avec pondération"""
    WEIGHTS = {
        'rss': 1.5,
        'reddit': 1.0,
        'bluesky': 1.2
    }
    
    # Mélanger et trier par score pondéré
    weighted_articles = []
    for source, articles in remaining_articles.items():
        for article in articles:
            weighted_score = article.relevance_score * WEIGHTS[source]
            weighted_articles.append((weighted_score, article))
    
    weighted_articles.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in weighted_articles[:flexible_slots]]

def select_articles_for_summary(articles_by_source: list[dict], max_days: int) -> list[dict]:
    """
    Fonction principale qui orchestre la sélection des articles
    
    Args:
        articles_by_source: {'rss': [...], 'reddit': [...], 'bluesky': [...]}
        max_days: Fenêtre temporelle (MAX_DAYS depuis .env)
    
    Returns:
        Liste des articles sélectionnés et équilibrés
    """
    total_count = int(os.getenv('LIMIT_ARTICLES_TO_RESUME', 15))
    
    # ÉTAPE 1: Calculer les quotas de base (Phase 1)
    quotas = _calculate_quotas(total_count)
    # Résultat: {'rss_min': 6, 'reddit_min': 3, 'bluesky_min': 2, 'flexible': 4}
    
    # ÉTAPE 2: Ajuster selon la fraîcheur des RSS (Phase 4)
    quotas = _apply_freshness_adjustment(articles_by_source, quotas)
    # Peut modifier les quotas si RSS peu actifs
    
    # ÉTAPE 3: Sélectionner les articles garantis par quota
    selected_articles = []
    remaining_articles = {}
    
    for source in ['rss', 'reddit', 'bluesky']:
        articles = articles_by_source['source']
        quota_key = f'{source}_min'
        quota = quotas.get(quota_key, 0)
        
        # Trier par score de pertinence (supposant que c'est déjà fait)
        selected = articles[:quota]
        selected_articles.extend(selected)
        
        # Garder le reste pour la phase flexible
        remaining_articles[source] = articles[quota:]
    
    # ÉTAPE 4: Remplir les slots flexibles (Phase 2)
    if quotas['flexible'] > 0:
        flexible_articles = _fill_flexible_slots(remaining_articles, quotas['flexible'])
        selected_articles.extend(flexible_articles)
    
    return selected_articles[:total_count]  # Sécurité: ne pas dépasser