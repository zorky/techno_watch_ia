import logging
logging.basicConfig(level=logging.INFO)
from colorama import Fore
from core.logger import logger
from models.states import RSSState

def output_node(state: RSSState) -> RSSState:
    logger.info("📄 Affichage des résultats finaux")
    for item in state.summaries:
        print(
            Fore.CYAN
            + f"\n📰 {item['title']}\n"
            + Fore.CYAN
            + f"\n📈 {item['score']}\n"
            + Fore.GREEN
            + f"📝 {item['summary']}\n"
            + Fore.BLUE
            + f"🔗 {item['link']}\n"
            + f"⏱️ {item['published']}"
            + f"📡 {item['source']}"
        )
    return state