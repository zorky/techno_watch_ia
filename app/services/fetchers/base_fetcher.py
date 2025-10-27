from abc import ABC, abstractmethod
from app.services.models import Source


class BaseFetcher(ABC):
    @abstractmethod
    def fetch_articles(self, source: Source, max_days: int) -> list[dict]:
        pass
