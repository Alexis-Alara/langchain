import os
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from app.db.mongo import knowledge_collection as collection
from app.db.config import OPENAI_API_KEY

# Embeddings
embeddings_model = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Vector store global
vector_store = None

# Path local para guardar FAISS en disco
FAISS_PATH = "faiss_index"

def init_faiss():
    """
    Inicializa FAISS desde MongoDB o carga de disco si existe.
    """
    global vector_store
    
    print("=== Iniciando init_faiss ===")
    print(f"FAISS_PATH configurado en: {FAISS_PATH}")

    # Intentar cargar FAISS desde disco
    if os.path.exists(FAISS_PATH):
        print("→ Encontrado índice FAISS en disco, intentando cargar...")
        vector_store = FAISS.load_local(FAISS_PATH, embeddings_model)
        print("✅ FAISS cargado desde disco.")
        return

    # Sino, inicializar desde Mongo
    texts, metadatas = [], []
    for doc in collection.find({}):
        texts.append(doc["text"])
        metadatas.append({"tenant_id": doc.get("tenant_id")})

    if texts:
        vector_store = FAISS.from_texts(texts, embeddings_model, metadatas=metadatas)
        vector_store.save_local(FAISS_PATH)  # guardar en disco
        print("FAISS creado desde Mongo y guardado en disco.")
    else:
        vector_store = None
        print("Mongo vacío, FAISS no inicializado.")


def add_document(text: str, tenant_id: str):
    """
    Agrega un nuevo documento a Mongo y FAISS.
    """
    global vector_store

    # Insertar en Mongo
    emb = embeddings_model.embed_query(text)
    collection.insert_one({"text": text, "embedding": emb, "tenant_id": tenant_id})

    # Agregar a FAISS
    if vector_store is None:
        # Si no existe FAISS, inicializar con este documento
        vector_store = FAISS.from_texts([text], embeddings_model, metadatas=[{"tenant_id": tenant_id}])
    else:
        vector_store.add_texts([text], metadatas=[{"tenant_id": tenant_id}])

    # Guardar FAISS en disco
    vector_store.save_local(FAISS_PATH)
