#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent RSS avec résumé automatique via LLM local.

Ce script exécute ces actions, dans l'ordre :
- Lit une liste de flux RSS
- Filtre les articles selon des mots-clés
- Résume les articles avec un modèle LLM local (Ollama)
- Affiche les résultats en console

Framework : LangGraph pour le graphe des actions (noeuds)

Usage :
    python agent_rss.py --debug

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

 - un fichier .env est possible pour surcharger 3 variables : 
   LLM_MODEL (par défaut mistal), 
   LLM_TEMPERATURE (par défaut 0.3), 
   OLLAMA_BASE_URL (par défaut http://localhost:11434/v1)
   LIMIT_ARTICLES (par défaut -1 : pas de limite)
   RSS_URLS (par défaut la liste dans _get_rss_urls) : sur une seule ligne

   Exemple :

 LLM_MODEL=mistral
 # LLM_MODEL=llama3:8b-instruct-q4_K_M
 LLM_TEMPERATURE=0.7
 RSS_URLS=["https://belowthemalt.com/feed/","https://cosmo-games.com/sujet/ia/feed/","https://www.ajeetraina.com/rss/","https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"]


 - Ollama doit être exécuté en local avec le modèle pullé, ou tout autre serveur LLM

"""

import logging
import argparse
from colorama import Fore, Style, init
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel
from typing import List, Optional

# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

import feedparser
import os
import json
import opml

# =========================
# Init couleurs
# =========================
init(autoreset=True)

# =========================
# Parsing des arguments CLI
# =========================
parser = argparse.ArgumentParser(description="Agent RSS avec résumés LLM")
parser.add_argument("--debug", action="store_true", help="Active le mode debug détaillé")
args = parser.parse_args()

# =========================
# Formatter coloré
# =========================
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        levelname_color = color + record.levelname + Style.RESET_ALL
        record.levelname = levelname_color
        return super().format(record)

formatter = ColorFormatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
logger.addHandler(handler)
logger.propagate = False

# =========================
# Configuration du modèle
# =========================

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
# LLM_API = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1") # si ChatOpenAI
LLM_API = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") # si ChatOllama
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

llm = ChatOllama(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    base_url=LLM_API,  # http://localhost:11434
)

# llm = ChatOpenAI(
#     temperature=LLM_TEMPERATURE,
#     model=LLM_MODEL,
#     openai_api_base=LLM_API,
#     openai_api_key="dummy-key-ollama",
# )

# =========================
# Fonctions utilitaires
# =========================
def summarize_article(title, content):
    prompt = f"""Tu es un journaliste expert. Résume en français cet article en 3 phrases claires et concises.
Titre : {title}
Contenu : {content}
"""
    if args.debug:
        logger.debug(Fore.MAGENTA + "--- PROMPT ENVOYÉ AU LLM ---\n" + prompt + "\n---------------------------")
    result = llm.invoke(prompt)
    if args.debug:
        logger.debug(Fore.MAGENTA + "--- RÉPONSE BRUTE DU LLM ---\n" + str(result) + "\n---------------------------")
    return result.content.strip() if hasattr(result, "content") else str(result).strip()

def fetch_rss_articles(rss_urls):
    articles = []
    for url in rss_urls:
        logger.info(Fore.BLUE + f"Lecture du flux RSS : {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                "title": entry.title,
                "summary": entry.summary,
                "link": entry.link
            })
        logger.info(f"{len(feed.entries)} articles trouvés dans ce flux")
    logger.debug(f"{len(articles)} articles récupérés au total")
    return articles

def filter_articles_by_keywords(articles, keywords):
    filtered = []
    for article in articles:
        if any(k.lower() in article["title"].lower() or k.lower() in article["summary"].lower() for k in keywords):
            filtered.append(article)
    logger.debug(f"{len(filtered)} articles après filtrage")
    return filtered

def read_opml():
    o = opml.parse('my.opml')
    for x in o:
        logger.info(x.text)        
        for y in x:
            if y.type == "rss":            
                logger.info(y.xmlUrl)

# =========================
# Définition de l’état
# =========================
class RSSState(BaseModel):
    rss_urls: List[str]
    keywords: List[str]
    articles: Optional[List[dict]] = None
    filtered_articles: Optional[List[dict]] = None
    summaries: Optional[List[dict]] = None    

# =========================
# Nœuds du graphe
# =========================
def fetch_node(state: RSSState):
    logger.info("📥 Récupération des articles...")
    articles = fetch_rss_articles(state.rss_urls)
    logger.info(f"{len(articles)} articles récupérés")
    return state.model_copy(update={"articles": articles})

def filter_node(state: RSSState):
    logger.info("🔍 Filtrage des articles par mots-clés...")
    filtered = filter_articles_by_keywords(state.articles, state.keywords)
    logger.info(f"{len(filtered)} articles correspondent aux mots-clés")
    return state.model_copy(update={"filtered_articles": filtered})

def summarize_node(state: RSSState):
    logger.info("✏️  Résumé des articles filtrés...")
    LIMIT_ARTICLES = int(os.getenv("LIMIT_ARTICLES", -1))
    if LIMIT_ARTICLES > 0:
        logger.info(f"Limite de résumé à {LIMIT_ARTICLES} articles")
        articles = state.filtered_articles[:LIMIT_ARTICLES]
    else:
        logger.info("Pas de limite sur le nombre d'articles à résumer")
        articles = state.filtered_articles
    summaries = []
    for i, article in enumerate(articles, start=1):
        logger.info(Fore.YELLOW + f"Résumé {i}/{len(articles)} : {article['title']}")
        summary_text = summarize_article(article["title"], article["summary"])
        summaries.append({
            "title": article["title"],
            "summary": summary_text,
            "link": article["link"]
        })
    return state.model_copy(update={"summaries": summaries})

def output_node(state: RSSState):
    logger.info("📄 Affichage des résultats finaux")
    for item in state.summaries:
        print(Fore.CYAN + f"\n📰 {item['title']}\n" +
              Fore.GREEN + f"📝 {item['summary']}\n" +
              Fore.BLUE + f"🔗 {item['link']}")
    return state

# =========================
# Construction du graphe : noeuds (nodes) et transitions (edges)
# fetch -> filter -> summarize -> output
# =========================
def make_graph():
    graph = StateGraph(RSSState)
    graph.add_node("fetch", RunnableLambda(fetch_node))
    graph.add_node("filter", RunnableLambda(filter_node))
    graph.add_node("summarize", RunnableLambda(summarize_node))
    graph.add_node("output", RunnableLambda(output_node))

    graph.set_entry_point("fetch")
    graph.add_edge("fetch", "filter")
    graph.add_edge("filter", "summarize")
    graph.add_edge("summarize", "output")

    return graph.compile()

def _get_rss_urls():
    """
    Obtient la liste des URL RSS à traiter à partir des variables d'environnement.
    Le .env ne contient que des types string et au format JSON
    """
    default_list = [
        "https://cert.ssi.gouv.fr/alerte/feed/",
        "https://www.djangoproject.com/rss/community/",
        "https://cosmo-games.com/sujet/ia/feed/",
        "https://belowthemalt.com/feed/",
        "https://www.ajeetraina.com/rss/",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
    ]
    # ["https://cert.ssi.gouv.fr/feed/", "https://feeds.feedburner.com/TheHackersNews", "https://blog.cryptographyengineering.com/feed", "https://cybersecuritynews.com/feed/", "https://securityboulevard.com/feed/"]
    default_json = json.dumps(default_list)

    rss_urls_str = os.getenv("RSS_URLS", default_json)
    try:
        rss_urls = json.loads(rss_urls_str)
        if not isinstance(rss_urls, list):
            raise ValueError("RSS_URLS n'est pas une liste JSON valide")
    except (json.JSONDecodeError, ValueError):
        rss_urls = default_list

    return rss_urls

# =========================
# Main
# =========================
def main():
    logger.info(Fore.MAGENTA + Style.BRIGHT + "=== Agent RSS avec résumés LLM ===")
    logger.info(Fore.YELLOW + Style.BRIGHT + f"sur {LLM_API} avec {LLM_MODEL} sur une T° {LLM_TEMPERATURE}")
    agent = make_graph()
    rss_urls = _get_rss_urls()
    state = RSSState(
        rss_urls=rss_urls,
        keywords=["intelligence artificielle", "IA générative", "cybersécurité", "alerte sécurité"]
    )
    agent.invoke(state)

if __name__ == "__main__":
    main()
