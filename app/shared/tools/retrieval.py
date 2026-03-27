import logging

import app.shared.tools.embeddings as embeddings

logger = logging.getLogger(__name__)


def search_semantic(query: str, tenant_id: str, top_k: int = 3, k: int = None):
    limit = k if k is not None else top_k

    if embeddings.vector_store is None:
        embeddings.init_faiss()
    if embeddings.vector_store is None:
        logger.info("FAISS is not initialized. Returning no documents.")
        return []

    results = embeddings.vector_store.similarity_search(query, k=limit)
    filtered_results = [
        result
        for result in results
        if (result.metadata.get("tenant_id") or result.metadata.get("tenantId")) == tenant_id
    ]
    logger.info(
        "Semantic search query=%r tenant=%s raw=%s filtered=%s",
        query,
        tenant_id,
        len(results),
        len(filtered_results),
    )
    return filtered_results
