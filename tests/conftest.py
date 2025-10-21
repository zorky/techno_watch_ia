import pytest
import sys
from services.models import SourceType

@pytest.fixture(autouse=True, scope="session")
def mock_articles(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['pytest'])
    return [
        {"title": "Article RSS 1", "source": SourceType.RSS, "score": 0.9, "published": "2025-10-20"},
        {"title": "Article RSS 2", "source": SourceType.RSS, "score": 0.8, "published": "2025-10-20"},
        {"title": "Article Reddit 1", "source": SourceType.REDDIT, "score": 0.7, "published": "2025-10-20"},
        {"title": "Article Bluesky 1", "source": SourceType.BLUESKY, "score": 0.6, "published": "2025-10-20"},
        {"title": "Article RSS 3", "source": SourceType.RSS, "score": 0.5, "published": "2025-10-19"},
        {"title": "Article Reddit 2", "source": SourceType.REDDIT, "score": 0.4, "published": "2025-10-19"},
    ]

@pytest.fixture(autouse=True, scope="session")
def mock_env_vars(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['pytest'])
    monkeypatch.setenv("RSS_WEIGHT", "50")
    monkeypatch.setenv("REDDIT_WEIGHT", "30")
    monkeypatch.setenv("BLUESKY_WEIGHT", "20")
    monkeypatch.setenv("LIMIT_ARTICLES_TO_RESUME", "5")
    monkeypatch.setenv("FRESHNESS_BOOST_THRESHOLD", "0.3")
