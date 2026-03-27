import logging
import os

from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from app.shared.config.database import knowledge_collection
from app.shared.config.settings import FAISS_PATH, OPENAI_API_KEY

logger = logging.getLogger(__name__)

embeddings_model = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
vector_store = None


def _load_local_index():
    try:
        return FAISS.load_local(
            FAISS_PATH,
            embeddings_model,
            allow_dangerous_deserialization=True,
        )
    except TypeError:
        return FAISS.load_local(FAISS_PATH, embeddings_model)


def init_faiss():
    global vector_store

    if os.path.exists(FAISS_PATH):
        try:
            vector_store = _load_local_index()
            logger.info("FAISS loaded from disk: %s", FAISS_PATH)
            return
        except Exception as exc:
            logger.warning("Could not load FAISS from disk: %s", str(exc))

    texts = []
    metadatas = []
    for document in knowledge_collection.find({}):
        text = document.get("text")
        if not text:
            continue
        tenant_id = document.get("tenantId") or document.get("tenant_id")
        texts.append(text)
        metadatas.append(
            {
                "tenantId": tenant_id,
                "tenant_id": tenant_id,
                "source": document.get("source"),
                "_id": str(document.get("_id", "")),
            }
        )

    if texts:
        vector_store = FAISS.from_texts(texts, embeddings_model, metadatas=metadatas)
        vector_store.save_local(FAISS_PATH)
        logger.info("FAISS created from Mongo and saved to disk: %s", FAISS_PATH)
    else:
        vector_store = None
        logger.info("Knowledge base is empty. FAISS not initialized.")


def add_document(text: str, tenant_id: str):
    global vector_store

    embedding = embeddings_model.embed_query(text)
    knowledge_collection.insert_one(
        {
            "text": text,
            "embedding": embedding,
            "tenantId": tenant_id,
            "tenant_id": tenant_id,
        }
    )

    metadata = {"tenantId": tenant_id, "tenant_id": tenant_id}
    if vector_store is None:
        vector_store = FAISS.from_texts([text], embeddings_model, metadatas=[metadata])
    else:
        vector_store.add_texts([text], metadatas=[metadata])
    vector_store.save_local(FAISS_PATH)
