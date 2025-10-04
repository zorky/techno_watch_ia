import os
import logging
logging.basicConfig(level=logging.INFO)
from dotenv import load_dotenv
from colorama import Fore
from core.logger import logger
from models.states import RSSState

load_dotenv()
THRESHOLD_SEMANTIC_SEARCH = float(os.getenv("THRESHOLD_SEMANTIC_SEARCH", "0.5"))

def send_articles_node(state: RSSState) -> RSSState:
    from send_articles_email import send_watch_articles
    from models.emails import EmailTemplateParams

    logger.info("Envoi mail des articles")
    logger.info(f"Envoi de {len(state.summaries)} articles")
    if len(state.summaries) > 0:
        _params_mail = EmailTemplateParams(
            articles=state.summaries,
            keywords=state.keywords,
            threshold=THRESHOLD_SEMANTIC_SEARCH,
        )
        send_watch_articles(_params_mail)
    return state