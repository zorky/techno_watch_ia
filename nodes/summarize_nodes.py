import logging
logging.basicConfig(level=logging.INFO)
from colorama import Fore

from core.logger import logger
from models.states import RSSState
from services.models import SourceType, UnifiedState
from core.utils import measure_time, get_environment_variable, argscli
from services.model_service import set_prompt

MAX_DAYS = int(get_environment_variable("MAX_DAYS", "10"))

def _calculate_tokens(summary, elapsed):
    """Calcule le nombre approximatif de tokens dans un texte et le débit en tokens/s."""
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = len(enc.encode(summary))
    logger.info(
        f"Résumé : {tokens} tokens - débit approximatif {tokens / elapsed:.2f} tokens/s"
    )

@measure_time
def _summarize_article(title, content):    
    from services.model_service import init_llm_chat
    import time

    prompt = set_prompt("IA, ingénieurie logicielle et cybersécurité", title, content)

    if argscli.debug:
        logger.debug(
            Fore.MAGENTA
            + "--- PROMPT ENVOYÉ AU LLM ---\n"
            + prompt
            + "\n---------------------------"
        )
        start = time.time()

    # Appel au LLM
    llm = init_llm_chat()
    result = llm.invoke(prompt)
    summary = result.content.strip().strip('"').strip()

    if argscli.debug:
        end = time.time()
        elapsed = end - start
        _calculate_tokens(summary, elapsed)

    if argscli.debug:
        logger.debug(
            Fore.MAGENTA
            + "--- RÉPONSE BRUTE DU LLM ---\n"
            + str(result)
            + "\n---------------------------"
        )

    # Nettoyage des introductions génériques
    for prefix in ["Voici un résumé :", "Résumé :", "L'article explique que"]:
        if summary.startswith(prefix):
            summary = summary[len(prefix) :].strip()
    return summary


def summarize_node(state: UnifiedState) -> UnifiedState:
    from datetime import datetime, timezone
    from services.sources_ponderation import select_articles_for_summary

    logger.info("✏️  Résumé des articles filtrés...")
    LIMIT_ARTICLES_TO_RESUME = int(get_environment_variable("LIMIT_ARTICLES_TO_RESUME", -1))
    if LIMIT_ARTICLES_TO_RESUME > 0:
        logger.info(f"Limite de résumé à {LIMIT_ARTICLES_TO_RESUME} articles")
        articles = state.filtered_articles[:LIMIT_ARTICLES_TO_RESUME]
    else:
        logger.info("Pas de limite sur le nombre d'articles à résumer")
        articles = state.filtered_articles
    # dict Article : 'title', 'summary', 'link', 'published', 'score', 'source'        
    # article = articles[0]
    # logger.info(f"** 1er article à résumer : {article.keys()} {article.values()}")
    logger.info(f"{len(articles)} à résumer :")
    logger.info(f"{articles}")
    articles_to_summarise = select_articles_for_summary(articles, MAX_DAYS)
    logger.info(f"{len(articles_to_summarise)} articles sélectionnés pour résumé")
    summaries = []
    for i, article in enumerate(articles_to_summarise, start=1):        
        logger.info(Fore.YELLOW + f"Résumé {i}/{len(articles)} : {article['title']}")
        summary_text = _summarize_article(article["title"], article["summary"])
        summary = {
            "title": article["title"],
            "summary": summary_text,
            "link": article["link"],
            "score": article["score"],
            "published": article["published"],
            "dt_created": datetime.now(timezone.utc),
            "source": article["source"] if "source" in article else "unknown",
        }
        summaries.append(summary)
        logger.info(f"Ajout du résumé {summary}")
    return state.model_copy(update={"summaries": summaries})
