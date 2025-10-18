import logging
logging.basicConfig(level=logging.INFO)
from core.logger import logger
from colorama import Fore

def register_fetchers_auto():
    """Découvre automatiquement tous les BaseFetcher du module."""
    import importlib
    import pkgutil
    from services.factory_fetcher import FetcherRegistry
    
    MODULE_FETCHERS = "services.fetchers"
    logger.info(Fore.CYAN + f"🔍 Découverte automatique dans {MODULE_FETCHERS}")    
    
    fetchers_package = importlib.import_module(MODULE_FETCHERS)
    
    # Parcourt tous les sous-modules du package
    for importer, modname, ispkg in pkgutil.iter_modules(fetchers_package.__path__):
        if not ispkg:  # On ne veut que les modules, pas les sous-packages
            full_module_name = f"{MODULE_FETCHERS}.{modname}"
            try:
                # Importe dynamiquement chaque module
                importlib.import_module(full_module_name)
                logger.info(Fore.GREEN + f"✓ Module importé: {full_module_name}")
            except Exception as e:
                logger.error(Fore.RED + f"✗ Erreur import {full_module_name}: {e}")
                import traceback
                traceback.print_exc()
    
    # À ce stade, tous les décorateurs @fetcher_class ont été exécutés
    registered = FetcherRegistry.list_all()
    logger.info(Fore.GREEN + f"✓ Fetchers enregistrés: {registered}")
    return registered

# def register_fetchers_manual():
#     """À appeler une fois au démarrage de l'app."""
#     FetcherRegistry.register(RSSFetcher)
#     # FetcherRegistry.register(RedditFetcher)
#     # FetcherRegistry.register(BlueskyFetcher)
#     logger.info(f"Fetchers enregistrés: {FetcherRegistry.list_all()}")



