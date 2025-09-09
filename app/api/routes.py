from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.embeddings import add_document
from app.services.retrieval import search_semantic
from app.gpt import generate_answer
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.extension import Limiter
from app.chat_history import get_conversation_history, save_message

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# ---- MODELOS ----
class QueryRequest(BaseModel):
    question: str
    tenant_id: str
    conversation_id: str

class QueryResponse(BaseModel):
    answer: str

class AddDocRequest(BaseModel):
    text: str
    tenant_id: str


# ---- ENDPOINTS ----
@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")  # Limite de 5 x minuto por IP
async def query_endpoint(body: QueryRequest, request: Request):
    # Recuperar historial de la conversación
    history = get_conversation_history(body.tenant_id, body.conversation_id)

    # Guardar el mensaje del usuario
    save_message(body.tenant_id, body.conversation_id, "user", body.question)

    # Buscar contexto en FAISS
    docs = search_semantic(body.question, body.tenant_id)
    context = "\n".join([doc.page_content for doc in docs])
    
    # Generar respuesta con GPT usando historial + contexto
    answer = generate_answer(body.question, history=history, context=context)

    # Guardar la respuesta del bot en el historial
    save_message(body.tenant_id, body.conversation_id, "assistant", answer)

    # answer = generate_answer(body.question, body.tenant_id)
    return {"answer": answer}


@router.post("/add_document")
def add_document_endpoint(request: AddDocRequest):
    add_document(request.text, request.tenant_id)
    return {"status": "ok", "message": "Documento agregado correctamente."}
