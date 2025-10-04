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
from services.factory_fetcher import FetcherFactory
from services.models import Source, SourceType, UnifiedState

from core import logger

from nodes import unified_fetch_node

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
MODEL_EMBEDDINGS = "all-MiniLM-L6-v2"
# MODEL_EMBEDDINGS="all-mpnet-base-v2"

FILTER_KEYWORDS = os.getenv("FILTER_KEYWORDS", "").split(",")
THRESHOLD_SEMANTIC_SEARCH = float(os.getenv("THRESHOLD_SEMANTIC_SEARCH", "0.5"))
MAX_DAYS = int(os.getenv("MAX_DAYS", "10"))
OPML_FILE = os.getenv("OPML_FILE", "my.opml")
TOP_P = float(os.getenv("TOP_P", "0.5"))
MAX_TOKENS_GENERATE = int(os.getenv("MAX_TOKENS_GENERATE", "300"))


# =========================
# Configuration LLM local / saas
# =========================
def init_llm_chat():
    return ChatOpenAI(
        model=LLM_MODEL,
        openai_api_base=LLM_API,
        openai_api_key="dummy-key-ollama",
        temperature=LLM_TEMPERATURE,
        top_p=TOP_P,
        max_tokens=MAX_TOKENS_GENERATE,
    )
    # return ChatOllama(
    #     model=LLM_MODEL,
    #     temperature=LLM_TEMPERATURE,
    #     base_url=LLM_API,  # http://localhost:11434
    #     top_p=TOP_P,
    #     # num_predict=MAX_TOKENS,
    # )


llm = init_llm_chat()

# =========================
# Configuration du modèle d'embeddings
# Modèles disponibles et spécs :
# https://www.sbert.net/docs/sentence_transformer/pretrained_models.html
# =========================


def get_device_cpu_gpu_info():
    import torch

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(Fore.GREEN + f"GPU disponible : {gpu_name}")
        return "cuda"
    logger.info(Fore.YELLOW + "Aucun GPU disponible, utilisation du CPU.")
    return "cpu"


DEVICE_TYPE = get_device_cpu_gpu_info()


def init_sentence_model():
    logger.info(
        Fore.GREEN + f"Init SentenceTransformer {MODEL_EMBEDDINGS} sur {DEVICE_TYPE}"
    )
    return SentenceTransformer(MODEL_EMBEDDINGS, device=DEVICE_TYPE)
    # return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=DEVICE_TYPE)  # bon compromis pour le français/anglais
    # return SentenceTransformer('multi-qa-MiniLM-L6-cos-v1', device=DEVICE_TYPE)  # Optimisé pour la similarité


model = init_sentence_model()


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


@measure_time
def filter_articles_with_faiss(
    articles,
    keywords: list[str],
    threshold=0.7,
    index_path="keywords_index.faiss",
    show_progress=False,
):
    """
    Filtre les articles par similarité sémantique avec les mots-clés.
    :param articles: Liste de dicts avec 'title' et 'summary'
    :param keywords: Liste de mots-clés
    :param threshold: Seuil de similarité (0 à 1)
    :return: Articles filtrés
    """
    import faiss

    logger.info(f"Filtrage sémantique avec les mots-clés {keywords}")
    logger.info(f"Filtrage sémantique avec seuil {threshold}...")

    @measure_time
    def get_or_create_index(keywords, model, index_path):
        if os.path.exists(index_path):
            logger.info("🔍 Chargement de l'index FAISS existant...")
            return faiss.read_index(index_path)
        else:
            logger.info("🔧 Création d'un nouvel index FAISS...")
            keyword_embeddings = model.encode(
                keywords, convert_to_tensor=True, show_progress_bar=show_progress
            )
            keyword_embeddings = keyword_embeddings.cpu().numpy()
            faiss.normalize_L2(keyword_embeddings)
            index = faiss.IndexFlatIP(
                keyword_embeddings.shape[1]
            )  # Produit scalaire équivalent similarité cos
            index.add(keyword_embeddings)

            faiss.write_index(index, index_path)
            return index

    # Créer un index FAISS pour le produit scalaire (similarité cosinus)
    index = get_or_create_index(keywords, model, index_path)

    filtered = []
    for article in articles:
        text = f"{article['title']} {article['summary']}".strip()
        if not text:
            continue
        # cleaned_text = preprocess_text(text)

        article_embedding = model.encode(
            [text], convert_to_tensor=True, show_progress_bar=False
        )
        article_embedding = article_embedding.cpu().numpy()
        faiss.normalize_L2(article_embedding)  # Normaliser l'embedding de l'article

        # Recherche
        similarities, indices = index.search(
            article_embedding, k=len(keywords)
        )  # k = top N mot-clé le plus proche
        max_similarity = similarities[0].max()  # La similarité est déjà entre 0 et 1

        if max_similarity >= threshold:
            matched_keywords = [
                keywords[i] for i in indices[0] if similarities[0][i] >= threshold
            ]
            # logger.info(
            #     f"Similarities: {similarities[0]}, Indices: {indices[0]}"
            # )
            logger.info(
                f"✅ Article retenu (sim={max_similarity:.2f}, mots-clés: {matched_keywords}): {article['title']} {article['link']}"
            )            
            article["score"] = f"{max_similarity * 100:.1f}"
            logger.info(Fore.CYAN + f"{article['title']} {article['source']} -> {article['score']}")
            # logger.info(Fore.CYAN + Style.DIM + f"{article['source']}")
            filtered.append(article)

    logger.info(
        f"📊 {len(filtered)}/{len(articles)} articles après filtrage sémantique (seuil={threshold})"
    )
    return filtered


def set_prompt(theme, title, content):
    prompt = f"""Tu es un expert en {theme}. Résume **uniquement** l'article ci-dessous en **3 phrases maximales**, en français, avec :
1. L'information principale (qui ? quoi ?), précise s'il y a du code ou un projet avec du code.
2. Les détails clés (chiffres, noms, dates).
3. L'impact ou la solution proposée.

**Exemple :**
Titre : "Sortie de Python 3.12 avec un compilateur JIT"
Contenu : "Python 3.12 intègre un compilateur JIT expérimental..."
Résumé : Python 3.12 introduit un compilateur JIT expérimental pour accélérer l'exécution. Les tests montrent un gain de 10 à 30% sur certains workloads. Disponible en version bêta dès septembre 2025.

**À résumer :**
{title}

Contenu : {content}

Résumé :"""

    return prompt

    # minimaliste et original
    #     prompt = f"""Tu es un journaliste expert. Résume en français cet article en 3 phrases claires et concises.
    # Titre : {title}
    # Contenu : {content}
    # """
    # prompt technique à points
    #     prompt = f"""Tu es un expert en {theme}. Résume cet article en 3 phrases **techniquement précises**, en français, en extraant :
    # 1. L'information principale (ex: une découverte, une vulnérabilité, une sortie logicielle).
    # 2. Les détails clés (ex: versions concernées, acteurs impliqués, dates).
    # 3. L'impact ou la nouveauté (ex: "Cette faille affecte X utilisateurs", "Ce framework simplifie Y").
    # - Si le contenu est trop vague, réponds : "Résumé impossible : article incomplet ou non informatif.
    # - Si le contenu est en anglais, traduis-le d'abord en français avant de résumer.

    # **Titre :** {title}
    # **Contenu :** {content}

    # **Résumé :**"""
    # few-shot
    #     prompt = f"""Exemples de résumés attendus :
    # ---
    # Titre : "Découverte d'une faille critique dans OpenSSL 3.2"
    # Contenu : "La faille CVE-2024-1234 permet une exécution de code à distance..."
    # Résumé : OpenSSL 3.2 contient une faille critique (CVE-2024-1234) permettant une exécution de code à distance. Les versions 3.2.0 à 3.2.3 sont concernées. Les utilisateurs doivent mettre à jour immédiatement.
    # ---

    # Titre : "Meta présente Llama 3.1 avec 400M de paramètres"
    # Contenu : "Llama 3.1 introduit une architecture optimisée pour les devices mobiles..."
    # Résumé : Meta a lancé Llama 3.1, un modèle léger (400M de paramètres) optimisé pour les mobiles. Il surpasse les précédents modèles sur les benchmarks de latence. Disponible dès aujourd'hui en open source.
    # ---

    # **À toi :** Résume l'article suivant en suivant le même format.

    # **Titre :** {title}
    # **Contenu :** {content}

    # **Résumé :**"""


def _calculate_tokens(summary, elapsed):
    """Calcule le nombre approximatif de tokens dans un texte et le débit en tokens/s."""
    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = len(enc.encode(summary))
    logger.info(
        f"Résumé : {tokens} tokens - débit approximatif {tokens / elapsed:.2f} tokens/s"
    )


@measure_time
def summarize_article(title, content):
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

def filter_node(state: UnifiedState) -> RSSState:
    logger.info("🔍 Filtrage des articles par mots-clés...")

    filtered = filter_articles_with_faiss(
        state.articles, state.keywords, threshold=THRESHOLD_SEMANTIC_SEARCH
    )
    logger.info(f"{len(filtered)} articles correspondent aux mots-clés (sémantique)")

    return state.model_copy(update={"filtered_articles": filtered})


def summarize_node(state: RSSState) -> RSSState:
    from datetime import datetime, timezone
    from services.sources_ponderation import select_articles_for_summary

    logger.info("✏️  Résumé des articles filtrés...")
    LIMIT_ARTICLES_TO_RESUME = int(os.getenv("LIMIT_ARTICLES_TO_RESUME", -1))
    if LIMIT_ARTICLES_TO_RESUME > 0:
        logger.info(f"Limite de résumé à {LIMIT_ARTICLES_TO_RESUME} articles")
        articles = state.filtered_articles[:LIMIT_ARTICLES_TO_RESUME]
    else:
        logger.info("Pas de limite sur le nombre d'articles à résumer")
        articles = state.filtered_articles
    # dict Article : 'title', 'summary', 'link', 'published', 'score', 'source'        
    article = articles[0]
    logger.info(f"** 1er article à résumer : {article.keys()} {article.values()}")
    articles_to_summarise = select_articles_for_summary(articles, MAX_DAYS)
    logger.info(f"{len(articles_to_summarise)} articles sélectionnés pour résumé")
    summaries = []
    for i, article in enumerate(articles_to_summarise, start=1):        
        logger.info(Fore.YELLOW + f"Résumé {i}/{len(articles)} : {article['title']}")
        summary_text = summarize_article(article["title"], article["summary"])
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
