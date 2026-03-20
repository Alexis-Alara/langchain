from typing import List
from langchain.docstore.document import Document
import app.embeddings as embeddings


def search_semantic(query: str, tenant_id: str, k: int = 3) -> List[Document]:
    """
    Realiza una busqueda semantica en FAISS filtrando por tenant_id.
    """
    print(f"Realizando búsqueda semántica para tenant_id={tenant_id} y query='{query}'")

    if embeddings.vector_store is None:
        print("FAISS no está inicializado, intentando cargar...")
        embeddings.init_faiss()

    if embeddings.vector_store is None:
        return []

    results = embeddings.vector_store.similarity_search(query, k=k)
    filtered_results = [result for result in results if result.metadata.get("tenantId") == tenant_id]
    return filtered_results
