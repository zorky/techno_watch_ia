#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent RSS avec résumé automatique via LLM local.

Ce script / cli exécute ces actions, dans l'ordre :
- Lit une liste de flux RSS
- Filtre les articles selon des mots-clés
- Résume les articles avec un modèle LLM local (Ollama)
- Affiche les résultats en console
- Envoi la revue de veille par mail

Framework : LangGraph pour le graphe des actions (noeuds)

Usage :
    python main_agent_rss.py [--debug]

Installation et Configuration :

 - Installer les dépendances requises avec uv ou pip :

   ```
   uv venv
   source .venv/bin/activate # ou source .venv/Scripts/activate sous Windows
   uv sync --dev
   ```
   ou pip
   ```
   python3 -m venv .venv
   source .venv/bin/activate # ou source .venv/Scripts/activate sous Windows
   pip install -r requirements.txt
   ```
   paquets : langgraph, langchain, langchain_core, pydantic, feedparser

 - un fichier .env est possible pour surcharger des variables, voir le .env.example :

   LLM_MODEL (par défaut mistal),
   LLM_TEMPERATURE (par défaut 0.3),
   OLLAMA_BASE_URL (par défaut http://localhost:11434/v1)
   LIMIT_ARTICLES_TO_RESUME (par défaut -1 : pas de limite) : pour l'inférence, combien d'articles le LLM doit résumer ?
   RSS_URLS (par défaut la liste dans _get_rss_urls) : sur une seule ligne

   Exemple :

 LLM_MODEL=mistral
 # LLM_MODEL=llama3:8b-instruct-q4_K_M
 LLM_TEMPERATURE=0.7
 RSS_URLS=["https://belowthemalt.com/feed/","https://cosmo-games.com/sujet/ia/feed/","https://www.ajeetraina.com/rss/","https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"]


 - Ollama doit être exécuté en local avec le modèle pullé, ou tout autre serveur LLM

"""

import logging
from datetime import datetime, timedelta
from colorama import Fore, Style
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda

from langchain_openai import ChatOpenAI
# from langchain_ollama import ChatOllama

import feedparser
import os

from sentence_transformers import SentenceTransformer

from models.states import RSSState
from read_opml import parse_opml_to_rss_list

from bs4 import BeautifulSoup

from core import measure_time, argscli
# from services.factory_fetcher import FetcherFactory
from services.models import Source, SourceType, UnifiedState

from core import logger

from nodes import unified_fetch_node, filter_node, summarize_node
# from services.model_service import init_sentence_model #, model

# =========================
# Init du logging et logger
# Par défaut INFO
# Forcer à DEBUG : python main_agent_rss.py --debug
# =========================

logging.basicConfig(level=logging.INFO)

# =========================
# Configuration du modèle LLM et configurations recherche
# =========================

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
LLM_API = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")  # si ChatOpenAI
# LLM_API = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")  # si ChatOllama
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
# Modèles embeddings disponibles et spécs : https://www.sbert.net/docs/sentence_transformer/pretrained_models.html
# MODEL_EMBEDDINGS = "all-MiniLM-L6-v2"
# MODEL_EMBEDDINGS="all-mpnet-base-v2"

FILTER_KEYWORDS = os.getenv("FILTER_KEYWORDS", "").split(",")
THRESHOLD_SEMANTIC_SEARCH = float(os.getenv("THRESHOLD_SEMANTIC_SEARCH", "0.5"))
MAX_DAYS = int(os.getenv("MAX_DAYS", "10"))
OPML_FILE = os.getenv("OPML_FILE", "my.opml")
# TOP_P = float(os.getenv("TOP_P", "0.5"))
# MAX_TOKENS_GENERATE = int(os.getenv("MAX_TOKENS_GENERATE", "300"))

# =========================
# Fonctions utilitaires
# =========================

def preprocess_text(text):
    """For tests purposes - Prétraitement simple : tokenization, suppression des stopwords, lemmatisation."""
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    import nltk
    import string

    nltk.download("punkt_tab")
    nltk.download("stopwords")
    nltk.download("wordnet")

    # Tokenization
    tokens = word_tokenize(text.lower())
    # Suppression des stopwords et ponctuation
    tokens = [
        t
        for t in tokens
        if t not in stopwords.words("french") and t not in string.punctuation
    ]
    # Lemmatisation
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(t) for t in tokens]
    return " ".join(tokens)

def strip_html(text: str) -> str:
    """Supprime les balises HTML d'un texte pour n'avoir que du texte brut."""
    return BeautifulSoup(text, "html.parser").get_text()


def get_summary(entry: dict):
    """
    Affiche le résumé ou le contenu d'une entrée de flux RSS ou Atom
       RSS 2.0: 'summary'
       Atom: 'content'

    Args:
        entry: Une entrée de flux RSS/Atom.
    """
    if "content" in entry.keys():
        content: list[feedparser.FeedParserDict] = entry.get("content", [dict])
        return content[0].get("value", "Pas de résumé")

    return entry.get("summary", "Pas de résumé")


def add_article_with_entry_syndication(entry, articles, cutoff_date, recent_in_feed):
    """
    A partir du contenu d'une entrée entry, ajoute un article récent à la liste des articles à traiter.

    Args:
        entry: Un article du flux RSS/Atom.
        articles: La liste des articles à traiter.
        cutoff_date: La date limite pour qu'un article soit considéré comme récent.
        recent_in_feed: Le compteur d'articles récents dans le flux actuel.
    """
    # Récupération de la date de publication (priorité à published, sinon updated)
    published_time = None
    if hasattr(entry, "published_parsed"):
        published_time = datetime(*entry.published_parsed[:6])
    elif hasattr(entry, "updated_parsed"):
        published_time = datetime(*entry.updated_parsed[:6])

    # Vérification de la date
    is_recent = published_time and (published_time >= cutoff_date)
    logger.debug(
        f"Article: {getattr(entry, 'title', 'Sans titre')} "
        f"(publié le {published_time}) : {'récent' if is_recent else 'trop ancien' if published_time else 'date inconnue'}"
    )

    if is_recent:
        # Normalisation des champs (RSS/Atom)
        title = getattr(entry, "title", "Sans titre")
        summary = get_summary(entry)
        summary = strip_html(summary)  # Nettoyage du HTML
        logger.debug(f"Résumé brut (après nettoyage) : {summary}")
        link = getattr(entry, "link", "#")
        if isinstance(link, list):  # Cas Atom où link est un objet
            link = link[0].href if link else "#"
        logger.info(Fore.GREEN + f"🆕 Article récent : {title} ({link})")
        articles.append(
            {
                "title": title,
                "summary": summary,
                "link": link,
                "published": published_time.isoformat() if published_time else None,
                "score": "0 %",
            }
        )
        recent_in_feed += 1
    return recent_in_feed

# =========================
# Nœuds du graphe
# =========================

def create_legacy_wrapper(legacy_node_func):
    """
    Wrapper pour adapter les anciens nœuds RSSState vers UnifiedState
    """

    def wrapper(state: UnifiedState) -> UnifiedState:
        # Conversion UnifiedState -> RSSState
        legacy_state = RSSState(
            rss_urls=[s.url for s in state.sources if s.type == SourceType.RSS],
            keywords=state.keywords,
            articles=state.articles,
            filtered_articles=state.filtered_articles,
            summaries=state.summaries,
        )

        # Appel du nœud legacy
        result = legacy_node_func(legacy_state)

        # Conversion RSSState -> UnifiedState
        return UnifiedState(
            sources=state.sources,  # Garde les sources originales
            keywords=result.keywords,
            articles=result.articles,
            filtered_articles=result.filtered_articles,
            summaries=result.summaries,
        )

    return wrapper

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


def send_articles(state: RSSState) -> RSSState:
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


def save_articles(state: RSSState) -> RSSState:
    from db.db import save_to_db

    logger.info("Sauvegarde des articles résumés en DB")
    if len(state.summaries) > 0:
        save_to_db(state.summaries)
    return state


# =========================
# Construction du graphe : noeuds (nodes) et transitions (edges)
# fetch -> filter -> summarize -> output
# =========================
def make_graph():
    # graph = StateGraph(RSSState)
    # graph.add_node("fetch", RunnableLambda(fetch_node))

    graph = StateGraph(UnifiedState)
    graph.add_node("fetch", RunnableLambda(unified_fetch_node))
    graph.add_node("filter", RunnableLambda(create_legacy_wrapper(filter_node)))
    graph.add_node("summarize", RunnableLambda(create_legacy_wrapper(summarize_node)))
    graph.add_node("displayoutput", RunnableLambda(create_legacy_wrapper(output_node)))
    graph.add_node(
        "savedbsummaries", RunnableLambda(create_legacy_wrapper(save_articles))
    )
    graph.add_node(
        "sendsummaries", RunnableLambda(create_legacy_wrapper(send_articles))
    )

    graph.set_entry_point("fetch")
    graph.add_edge("fetch", "filter")
    graph.add_edge("filter", "summarize")
    graph.add_edge("summarize", "displayoutput")
    graph.add_edge("displayoutput", "savedbsummaries")
    graph.add_edge("savedbsummaries", "sendsummaries")

    return graph.compile()

def get_rss_urls():
    """
    Obtient la liste des URL RSS à traiter à partir des variables d'environnement.
    Le .env ne contient que des types string et au format JSON
    """
    logger.info("Obtention des URL RSS à traiter...")
    rss_list_opml = parse_opml_to_rss_list(OPML_FILE)

    return [
        Source(
            type=SourceType.RSS, name=feed.titre, url=feed.lien_rss, link=feed.lien_web
        )
        for feed in rss_list_opml
        if (
            logger.debug(f"Flux RSS : {feed.titre} - {feed.lien_rss} - {feed.lien_web}")
            or True
        )
    ]

def load_sources_from_config(config_path: str, type_source: SourceType) -> list[Source]:
    """
    Support pour un fichier JSON qui peut inclure Reddit et Bluesky
    Exemple de structure :
    {
        "sources": [            
            {
                "type": "reddit",
                "subreddit": "MachineLearning",
                "name": "ML Reddit",
                "sort_by": "hot",
                "time_filter": "day"
            },
            {
                "type": "bluesky",
                "url": "@user.bsky.social",
                "name": "Tech Expert"
            },
            {
                "type": "bluesky",
                "url": "firehose",
                "name": "Bluesky Public Feed"
            }
        ]
    }
    """
    import json
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    sources = []
    for source_config in config.get('sources', []):
        if source_config['type'] == type_source.REDDIT:
            sources.append(Source(
                type=SourceType.REDDIT,
                url=f"reddit.com/r/{source_config['subreddit']}",
                name=source_config.get('name'),
                subreddit=source_config['subreddit'],
                sort_by=source_config.get('sort_by', 'hot'),
                time_filter=source_config.get('time_filter', 'day')
            ))
        elif source_config['type'] == type_source.BLUESKY:
            sources.append(Source(
                type=SourceType.BLUESKY,
                url=source_config['url'],
                name=source_config.get('name')
            ))
        # else:  # RSS
        #     sources.append(Source(
        #         type=SourceType.RSS,
        #         url=source_config['url'],
        #         name=source_config.get('name')
        #     ))
    
    return sources

def get_subs_reddit_urls():
    """
    Obtient la liste des URL Reddit à traiter à partir du fichier myreddit.json
    """    
    MY_REDDIT_FILE = os.getenv("REDDIT_FILE", "myreddit.json")    
    return load_sources_from_config(MY_REDDIT_FILE, SourceType.REDDIT)
    
def _show_graph(graph):
    """Affichage du graphe / automate LangGraph qui est utilisé"""

    def _get_graph(_graph):
        return _graph.get_graph()

    def _display_graph_matplot(_graph):
        import matplotlib.pyplot as plt
        import matplotlib.image as mpimg
        import io

        # plt.ion()
        png_data = _get_graph(_graph).draw_mermaid_png()
        img = mpimg.imread(io.BytesIO(png_data), format="PNG")
        plt.imshow(img)
        plt.axis("off")
        plt.show()
        plt.pause(0.001)

    def _display_graph_ascii(_graph):
        print(_get_graph(_graph).draw_ascii())

    def _display_device(_graph):
        from IPython.display import Image, display

        display(Image(_get_graph(_graph).draw_mermaid_png()))

    try:
        # _display_graph_matplot(graph)
        _display_graph_ascii(graph)
    except Exception as e:
        logger.error(f"{e}")

def prepare_data():
    sources_urls = get_rss_urls()
    reddit_subs= get_subs_reddit_urls()
    sources_urls.extend(reddit_subs)

    logger.info(f"{len(sources_urls)} flux RSS à traiter")
    initial_state = UnifiedState(
        sources=sources_urls,
        keywords=FILTER_KEYWORDS
        if FILTER_KEYWORDS != [""]
        else ["intelligence artificielle", "IA", "cybersécurité", "alerte sécurité"],
    )
    return initial_state

# =========================
# Main
# =========================
def main():
    from db.db import init_db

    logger.info(Fore.MAGENTA + Style.BRIGHT + "=== Agent RSS avec résumés LLM ===")
    logger.info(
        Fore.YELLOW
        + Style.BRIGHT
        + f"sur {LLM_API} avec {LLM_MODEL} sur une T° {LLM_TEMPERATURE} sur les {MAX_DAYS} derniers jours"
    )
    logger.info(Fore.YELLOW + f"Initialisation DB")
    init_db()

    initial_state = prepare_data()

    agent = make_graph()

    if argscli.debug:
        logger.info(f"🤖 LangGraph déroulera cet automate...")
        _show_graph(agent)

    agent.invoke(initial_state)


def search():
    from db.db import (
        search_fts,              
        init_db,
    )
    
    init_db()    
    search_fts("python")


if __name__ == "__main__":
    main()
    # search()
