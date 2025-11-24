from typing import List
from app.embeddings import vector_store
import app.embeddings as embeddings

def search_semantic(query: str, tenant_id: str, k: int = 3) -> List[str]:
    """
    Realiza una búsqueda semántica en FAISS filtrando por tenant_id.

    Args:
        query (str): Pregunta del usuario
        tenant_id (str): ID del cliente/tenant
        k (int): Número de resultados a devolver

    Returns:
        List[str]: Lista de textos relevantes
    """
    print(f"Realizando búsqueda semántica para tenant_id={tenant_id} y query='{query}'")
    if embeddings.vector_store is None:
        print("FAISS no está inicializado, intentando cargar...")
        embeddings.init_faiss()
        
    # if vector_store is None:
    #     print("FAISS no está inicializado.")
    #     # FAISS aún no inicializado o Mongo vacío
    #     return []

    # Realiza la búsqueda
    results = embeddings.vector_store.similarity_search(query, k=k)
    filtered_results = [r for r in results if r.metadata.get("tenantId") == tenant_id]
    return filtered_results
    #results = vector_store.similarity_search(query, k=k)
    # print(f"Resultados sin filtrar: {len(results)}")

    # # Filtra por tenant_id
    # filtered_results = [
    #     r.page_content for r in results
        
    #     if r.metadata.get("tenant_id") == tenant_id
        
        
    # ]
    # print(f"Resultados filtrados por tenant_id={tenant_id}: {len(filtered_results)}")
    # print("Contenido de los resultados filtrados:")
    # for i, doc in enumerate(filtered_results, 1):
    #     print(f"{i}: {doc}")
    # return filtered_results
