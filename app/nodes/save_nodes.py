import logging
logging.basicConfig(level=logging.INFO)
from colorama import Fore
from app.core.logger import logger
from app.models.states import RSSState
from app.db import save_to_db

def save_articles_node(state: RSSState) -> RSSState:    
    logger.info(Fore.LIGHTWHITE_EX + "Sauvegarde des articles résumés en DB")
    if len(state.summaries) > 0:
        save_to_db(state.summaries)
    return state
