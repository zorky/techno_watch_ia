import os
import logging
logging.basicConfig(level=logging.INFO)
from colorama import Fore

from core.logger import logger
from services.models import UnifiedState
from core.utils import measure_time, get_environment_variable

THRESHOLD_SEMANTIC_SEARCH = float(get_environment_variable("THRESHOLD_SEMANTIC_SEARCH", "0.5"))

@measure_time
def _filter_articles_with_faiss(
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
    from services.model_service import init_sentence_model
    model = init_sentence_model()

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
            filtered.append(article)

    logger.info(
        f"📊 {len(filtered)}/{len(articles)} articles après filtrage sémantique (seuil={threshold})"
    )
    return filtered

def filter_node(state: UnifiedState) -> UnifiedState:
    from core.logger import count_by_type_articles
    logger.info("🔍 Filtrage des articles par mots-clés...")

    filtered = _filter_articles_with_faiss(
        state.articles, state.keywords, threshold=THRESHOLD_SEMANTIC_SEARCH
    )
    logger.info(f"{len(filtered)} articles correspondent aux mots-clés (sémantique)")
    count_by_type_articles("Nombre d'articles filtrés par sources", filtered) # OK

    return state.model_copy(update={"filtered_articles": filtered})