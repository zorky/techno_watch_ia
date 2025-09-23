from services.models import SourceType
from services.base_fetcher import BaseFetcher

class FetcherFactory:
    _fetchers = {}
    
    @classmethod
    def register_fetcher(cls, source_type: SourceType, fetcher_class: type):
        cls._fetchers[source_type] = fetcher_class
    
    @classmethod
    def create_fetcher(cls, source_type: SourceType, **kwargs) -> BaseFetcher:
        if source_type not in cls._fetchers:
            raise ValueError(f"No fetcher registered for {source_type}")
        return cls._fetchers[source_type](**kwargs)
