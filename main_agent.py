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

from models.states import RSSState
from read_opml import parse_opml_to_rss_list

from bs4 import BeautifulSoup

from core import argscli
from services.models import Source, SourceType, UnifiedState

from core import logger, get_environment_variable

from nodes import filter_node, summarize_node, \
                  output_node, save_articles_node, send_articles_node

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

# LLM_MODEL = get_environment_variable("LLM_MODEL", "mistral")
LLM_MODEL = get_environment_variable("LLM_MODEL", "mistral")
LLM_API = get_environment_variable("OLLAMA_BASE_URL", "http://localhost:11434/v1")  # si ChatOpenAI
# LLM_API = get_environment_variable("OLLAMA_BASE_URL", "http://localhost:11434")  # si ChatOllama
LLM_TEMPERATURE = float(get_environment_variable("LLM_TEMPERATURE", "0.3"))
# Modèles embeddings disponibles et spécs : https://www.sbert.net/docs/sentence_transformer/pretrained_models.html
# MODEL_EMBEDDINGS = "all-MiniLM-L6-v2"
# MODEL_EMBEDDINGS="all-mpnet-base-v2"

FILTER_KEYWORDS = get_environment_variable("FILTER_KEYWORDS", "").split(",")
THRESHOLD_SEMANTIC_SEARCH = float(get_environment_variable("THRESHOLD_SEMANTIC_SEARCH", "0.5"))
MAX_DAYS = int(get_environment_variable("MAX_DAYS", "10"))
OPML_FILE = get_environment_variable("OPML_FILE", "my.opml")
# TOP_P = float(get_environment_variable("TOP_P", "0.5"))
# MAX_TOKENS_GENERATE = int(get_environment_variable("MAX_TOKENS_GENERATE", "300"))

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

# =========================
# Construction du graphe : noeuds (nodes) et transitions (edges)
# fetch -> filter -> summarize -> output
# =========================
def make_graph():
    from nodes import dispatch_node, fetch_rss_node, fetch_reddit_node, merge_fetched_articles
    # graph = StateGraph(RSSState)
    # graph.add_node("fetch", RunnableLambda(fetch_node))

    graph = StateGraph(UnifiedState)

    # à splitter en des noeuds fetcher pour exécution //
    # graph.add_node("fetch", RunnableLambda(unified_fetch_node)) 
    graph.add_node("dispatch", RunnableLambda(dispatch_node))

    # noeuds fetchers
    graph.add_node("fetch_rss", RunnableLambda(fetch_rss_node))
    graph.add_node("fetch_reddit", RunnableLambda(fetch_reddit_node))

    # noeud de fusion des N fetchers précédents
    graph.add_node("merge_articles", RunnableLambda(merge_fetched_articles))

    graph.add_node("filter", RunnableLambda(filter_node))
    graph.add_node("summarize", RunnableLambda(summarize_node))
    graph.add_node("displayoutput", RunnableLambda(create_legacy_wrapper(output_node)))
    graph.add_node(
        "savedbsummaries", RunnableLambda(create_legacy_wrapper(save_articles_node))
    )
    graph.add_node(
        "sendsummaries", RunnableLambda(create_legacy_wrapper(send_articles_node))
    )
    #
    # les transitions entre les noeuds
    #

    # dispatch vers les fetchers
    graph.set_entry_point("dispatch")
    graph.add_edge("dispatch", "fetch_rss")
    graph.add_edge("dispatch", "fetch_reddit")
    
    # des fetchers vers le noeud de fusion des articles    
    graph.add_edge("fetch_rss", "merge_articles")
    graph.add_edge("fetch_reddit", "merge_articles")
    
    # on fusionne le tout
    graph.add_edge("merge_articles", "filter")    
    
    graph.add_edge("filter", "summarize")
    graph.add_edge("summarize", "displayoutput")
    graph.add_edge("displayoutput", "savedbsummaries")
    graph.add_edge("savedbsummaries", "sendsummaries")

    return graph.compile()

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
    initial_state = UnifiedState(        
        sources=[],
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
