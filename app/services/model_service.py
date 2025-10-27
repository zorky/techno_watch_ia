import logging

logging.basicConfig(level=logging.INFO)

from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
# from langchain_ollama import ChatOllama

from colorama import Fore

from app.core.logger import logger
from app.core.utils import get_environment_variable

# =========================
# Configuration du modèle LLM inférence
# =========================

LLM_MODEL = get_environment_variable("LLM_MODEL", "mistral")
LLM_API = get_environment_variable(
    "OLLAMA_BASE_URL", "http://localhost:11434/v1"
)  # si ChatOpenAI
# LLM_API = get_environment_variable("OLLAMA_BASE_URL", "http://localhost:11434")  # si ChatOllama
LLM_TEMPERATURE = float(get_environment_variable("LLM_TEMPERATURE", "0.3"))

TOP_P = float(get_environment_variable("TOP_P", "0.5"))
MAX_TOKENS_GENERATE = int(get_environment_variable("MAX_TOKENS_GENERATE", "300"))


# =========================
# Configuration LLM local / saas
# =========================
def init_llm_chat():
    logger.info(
        Fore.GREEN
        + f"Init LLM Chat Model {LLM_MODEL} via API {LLM_API} (temp={LLM_TEMPERATURE}, top_p={TOP_P})"
    )
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


def init_sentence_model():
    MODEL_EMBEDDINGS = get_environment_variable("MODEL_EMBEDDINGS")
    DEVICE_TYPE = get_device_cpu_gpu_info()
    logger.info(
        Fore.GREEN + f"Init SentenceTransformer {MODEL_EMBEDDINGS} sur {DEVICE_TYPE}"
    )
    return SentenceTransformer(MODEL_EMBEDDINGS, device=DEVICE_TYPE)
    # return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=DEVICE_TYPE)  # bon compromis pour le français/anglais
    # return SentenceTransformer('multi-qa-MiniLM-L6-cos-v1', device=DEVICE_TYPE)  # Optimisé pour la similarité


# =========================
# Le prompt pour le résumé à réaliser
# =========================


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
