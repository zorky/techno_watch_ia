import logging
logging.basicConfig(level=logging.INFO)

from sentence_transformers import SentenceTransformer
from core.logger import logger
from colorama import Fore

# =========================
# Configuration du modèle d'embeddings
# Modèles disponibles et spécs :
# https://www.sbert.net/docs/sentence_transformer/pretrained_models.html
# =========================

MODEL_EMBEDDINGS = "all-MiniLM-L6-v2"
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


# model = init_sentence_model()