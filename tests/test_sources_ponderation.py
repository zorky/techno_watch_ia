from unittest.mock import patch
from nodes.summarize_nodes import summarize_node
from services.models import SourceType, UnifiedState
from services.sources_ponderation import select_articles_for_summary


def test_select_articles_for_summary_basic(mock_articles, mock_env_vars):
    selected = select_articles_for_summary(mock_articles)
    assert len(selected) == 5
    # Vérifie que les quotas de base sont respectés
    rss_count = len([a for a in selected if a["source"] == SourceType.RSS])
    reddit_count = len([a for a in selected if a["source"] == SourceType.REDDIT])
    bluesky_count = len([a for a in selected if a["source"] == SourceType.BLUESKY])
    assert rss_count == 3  # 50% de 5 = 2.5 → 3 (arrondi)
    assert reddit_count == 2  # 30% de 5 = 1.5 → 2 (arrondi)
    assert bluesky_count == 0  # 20% de 5 = 1, mais priorité aux autres si flexible

def test_select_articles_for_summary_freshness_boost(mock_articles, mock_env_vars):
    # Simule un manque de fraîcheur RSS
    old_articles = [a for a in mock_articles if a["source"] == SourceType.RSS]
    old_articles = [{"title": "Old RSS", "source": SourceType.RSS, "score": 0.1, "published": "2025-10-10"}] * 2
    mixed_articles = old_articles + [a for a in mock_articles if a["source"] != SourceType.RSS]
    selected = select_articles_for_summary(mixed_articles)
    # Vérifie que le boost a augmenté la part des autres sources
    reddit_count = len([a for a in selected if a["source"] == SourceType.REDDIT])
    bluesky_count = len([a for a in selected if a["source"] == SourceType.BLUESKY])
    assert reddit_count + bluesky_count >= 2  # Au moins 2 slots flexibles attribués aux autres

def test_select_articles_for_summary_empty_source(mock_env_vars):
    articles = [{"title": "Only Reddit", "source": SourceType.REDDIT, "score": 0.7, "published": "2025-10-20"}] * 3
    selected = select_articles_for_summary(articles)
    assert len(selected) == 3
    assert all(a["source"] == SourceType.REDDIT for a in selected)

def test_select_articles_for_summary_limit(mock_articles, mock_env_vars):
    # Teste que la limite finale est bien appliquée
    selected = select_articles_for_summary(mock_articles)
    assert len(selected) <= 5

def test_summarize_node_limit(mock_articles, mock_env_vars):
    # state = UnifiedState(filtered_articles=mock_articles)
    state = UnifiedState(filtered_articles=mock_articles, keywords=[])
    with patch("nodes.summarize_nodes._summarize_article", return_value="Mock summary"):
        result = summarize_node(state)
        assert len(result.summaries) == 5
        assert all(s["summary"] == "Mock summary" for s in result.summaries)