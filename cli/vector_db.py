def filter_articles_with_tfidf(articles, keywords, threshold=0.3):
    """
    Filtre les articles par similarité sémantique avec les mots-clés.
    :param articles: Liste de dicts avec 'title' et 'summary'
    :param keywords: Liste de mots-clés
    :param threshold: Seuil de similarité (0 à 1)
    :return: Articles filtrés
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [f"{a['title']} {a['summary']}" for a in articles]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    keyword_matrix = vectorizer.transform(keywords)

    similarities = cosine_similarity(tfidf_matrix, keyword_matrix)
    max_similarities = similarities.max(axis=1)

    filtered = [
        article
        for i, article in enumerate(articles)
        if max_similarities[i] >= threshold
    ]
    return filtered