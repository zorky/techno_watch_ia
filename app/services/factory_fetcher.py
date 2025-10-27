from typing import Dict, Type
import logging

logging.basicConfig(level=logging.INFO)

from app.core.logger import logger
from app.services.models import SourceType
from app.services.fetchers.base_fetcher import BaseFetcher


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


class FetcherRegistry:
    """Registry qui auto-découvre les sous-classes de BaseFetcher."""

    _fetchers: Dict[str, Type[BaseFetcher]] = {}
    _instances: Dict[str, BaseFetcher] = {}

    @classmethod
    def register(cls, fetcher_class: Type[BaseFetcher]):
        """
        Enregistre une classe fetcher automatiquement.
        Peut être utilisé comme décorateur de classe !
        """
        if not issubclass(fetcher_class, BaseFetcher):
            raise TypeError(f"{fetcher_class} must inherit from BaseFetcher")

        source_type = fetcher_class.source_type
        if not source_type:
            raise ValueError(f"{fetcher_class.__name__} must define source_type")

        cls._fetchers[source_type] = fetcher_class
        logger.debug(f"✓ Fetcher enregistré: {source_type} -> {fetcher_class.__name__}")
        return fetcher_class  # Important pour que le décorateur retourne la classe

    @classmethod
    def get_fetcher(cls, source_type: str) -> BaseFetcher:
        """Crée une instance du fetcher demandé."""
        if source_type not in cls._fetchers:
            raise ValueError(f"Fetcher '{source_type}' not registered")

        if source_type not in cls._instances:
            cls._instances[source_type] = cls._fetchers[source_type]()

        return cls._instances[source_type]

    @classmethod
    def get_active_fetchers(cls, config: dict) -> Dict[str, BaseFetcher]:
        """Retourne les fetchers actifs selon la configuration."""
        active = {}
        for source_type, fetcher_class in cls._fetchers.items():
            env_flag = fetcher_class.env_flag
            if config.get(env_flag, False):
                active[source_type] = cls.get_fetcher(source_type)
                logger.debug(f"✓ Fetcher activé: {source_type}")
        return active

    @classmethod
    def list_all(cls) -> dict:
        """Liste tous les fetchers enregistrés."""
        return {k: v.__name__ for k, v in cls._fetchers.items()}
