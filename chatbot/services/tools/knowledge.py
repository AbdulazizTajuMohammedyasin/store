import numpy as np
from langchain.tools import tool

from chatbot.models import KnowledgeArticle
from chatbot.services import embeddings

RESULT_LIMIT = 3


def _backfill_missing_embeddings():
    """
    Compute and store embeddings for any article that doesn't have one
    yet (e.g. freshly seeded via a data migration, which doesn't trigger
    the post_save signal since migrations use historical model classes).
    """
    for article in KnowledgeArticle.objects.filter(embedding__isnull=True):
        article.embedding = embeddings.embed_text(
            f"{article.title}\n\n{article.content}"
        )
        article.save(update_fields=["embedding"])


def search_knowledge_base(query: str, limit: int = RESULT_LIMIT):
    _backfill_missing_embeddings()

    articles = list(KnowledgeArticle.objects.exclude(embedding__isnull=True))

    if not articles:
        return "No knowledge base articles are available."

    query_vector = np.array(embeddings.embed_text(query))
    article_vectors = np.array([article.embedding for article in articles])

    query_unit = query_vector / np.linalg.norm(query_vector)
    article_units = article_vectors / np.linalg.norm(
        article_vectors, axis=1, keepdims=True
    )

    similarities = article_units @ query_unit

    ranked = sorted(
        zip(articles, similarities),
        key=lambda pair: pair[1],
        reverse=True,
    )[:limit]

    return [
        {
            "title": article.title,
            "category": article.category,
            "content": article.content,
        }
        for article, _score in ranked
    ]


@tool
def knowledge_base_search(query: str):
    """
    Search the store's knowledge base for information about shipping,
    returns, payment methods, and frequently asked questions.
    """

    return search_knowledge_base(query)
