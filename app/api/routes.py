from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.embeddings import add_document
from app.services.retrieval import search_semantic
from app.gpt import generate_answer
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.extension import Limiter
from app.chat_history import get_conversation_history, save_message
from app.services.whatsapp import whatsapp_service
import json
import logging
import hashlib
import hmac
import os

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

# ---- MODELOS WHATSAPP ----
class WhatsAppContact(BaseModel):
    profile: Dict[str, str]
    wa_id: str

class WhatsAppText(BaseModel):
    body: str

class WhatsAppMessage(BaseModel):
    from_: str = None
    id: str
    timestamp: str
    text: Optional[WhatsAppText] = None
    type: str
    
    class Config:
        fields = {'from_': 'from'}

class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: Dict[str, Any]
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None

class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str

class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]

class WhatsAppWebhook(BaseModel):
    object: str
    entry: List[WhatsAppEntry]

class WhatsAppSendMessage(BaseModel):
    messaging_product: str = "whatsapp"
    to: str
    type: str = "text"
    text: Dict[str, str]


# ---- ENDPOINTS ----
@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")  # Limite de 5 x minuto por IP
async def query_endpoint(body: QueryRequest, request: Request):
    tenant_id = request.headers.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant-id header is required")
    # Recuperar historial de la conversación
    history = get_conversation_history(tenant_id, body.conversation_id)

    # Guardar el mensaje del usuario
    
    save_message(tenant_id, body.conversation_id, "user", body.question)

    # Buscar contexto en FAISS
    docs = search_semantic(body.question, tenant_id)
    context = "\n".join([doc.page_content for doc in docs])
    
    # Generar respuesta con GPT usando historial + contexto
    answer = generate_answer(body.question, history=history, context=context, tenant_id=tenant_id, conversation_id=body.conversation_id, source="web")

    # Guardar la respuesta del bot en el historial
    save_message(tenant_id, body.conversation_id, "assistant", answer)

    # answer = generate_answer(body.question, tenant_id)
    return {"answer": answer}


# @router.post("/add_document")
# def add_document_endpoint(request: AddDocRequest):
#     add_document(request.text, request.tenant_id)
#     return {"status": "ok", "message": "Documento agregado correctamente."}


# ---- ENDPOINTS WHATSAPP ----
@router.get("/whatsapp/webhook")
async def whatsapp_webhook_verification(request: Request):
    """Endpoint para verificación del webhook de WhatsApp"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    # Verifica el token usando el servicio de WhatsApp
    verify_token = whatsapp_service.verify_token
    
    if mode == "subscribe" and token == verify_token:
        logging.info("Webhook verificado exitosamente")
        return int(challenge)
    else:
        raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/whatsapp/webhook")
@limiter.limit("20/minute")  # Limite más alto para WhatsApp
async def whatsapp_webhook_handler(body: WhatsAppWebhook, request: Request):
    """Endpoint para recibir mensajes de WhatsApp"""
    logging.info("Webhook de WhatsApp recibido")
    try:
        logging.info("Webhook de WhatsApp recibido")
        tenant_id = 'cliente1'
        
        for entry in body.entry:
            for change in entry.changes:
                if change.field == "messages":
                    value = change.value
                    
                    if value.messages:
                        for message in value.messages:
                            if message.type == "text" and message.text:
                                # Extraer información del mensaje
                                phone_number = whatsapp_service.format_phone_number(message.from_)
                                message_text = message.text.body
                                conversation_id = f"whatsapp_{phone_number}"
                                
                                # Log del mensaje recibido
                                logging.info(f"Mensaje recibido de {phone_number}: {message_text}")
                                
                                # Procesar el mensaje similar al endpoint query
                                history = get_conversation_history(tenant_id, conversation_id)
                                save_message(tenant_id, conversation_id, "user", message_text)
                                
                                # Buscar contexto y generar respuesta
                                docs = search_semantic(message_text, tenant_id)
                                context = "\n".join([doc.page_content for doc in docs])
                                answer = generate_answer(message_text, history=history, context=context)
                                
                                # Guardar respuesta del bot
                                save_message(tenant_id, conversation_id, "assistant", answer)
                                
                                # Enviar respuesta usando el servicio de WhatsApp
                                await whatsapp_service.send_text_message(phone_number, answer)
                                
                                logging.info(f"Respuesta enviada a {phone_number}: {answer[:100]}...")
        
        return {"status": "success"}
    
    except Exception as e:
        logging.error(f"Error procesando webhook de WhatsApp: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/whatsapp/send")
@limiter.limit("10/minute")
async def send_whatsapp_message_endpoint(message: WhatsAppSendMessage, request: Request):
    """Endpoint para enviar mensajes de WhatsApp manualmente"""
    tenant_id = request.headers.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant-id header is required")
    
    try:
        # Formatear número de teléfono
        formatted_phone = whatsapp_service.format_phone_number(message.to)
        
        # Enviar mensaje usando el servicio
        result = await whatsapp_service.send_text_message(formatted_phone, message.text["body"])
        
        # Guardar en el historial
        conversation_id = f"whatsapp_{formatted_phone}"
        save_message(tenant_id, conversation_id, "assistant", message.text["body"])
        
        return {"status": "success", "message_id": result.get("messages", [{}])[0].get("id")}
    except Exception as e:
        logging.error(f"Error enviando mensaje de WhatsApp: {str(e)}")
        raise HTTPException(status_code=500, detail="Error enviando mensaje")


# Endpoint adicional para enviar plantillas
@router.post("/whatsapp/send-template")
@limiter.limit("5/minute")
async def send_whatsapp_template_endpoint(request: Request, 
                                        to: str, 
                                        template_name: str, 
                                        language_code: str = "es"):
    """Endpoint para enviar plantillas de WhatsApp"""
    tenant_id = request.headers.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant-id header is required")
    
    try:
        # Formatear número de teléfono
        formatted_phone = whatsapp_service.format_phone_number(to)
        
        # Enviar plantilla usando el servicio
        result = await whatsapp_service.send_template_message(formatted_phone, template_name, language_code)
        
        return {"status": "success", "message_id": result.get("messages", [{}])[0].get("id")}
    except Exception as e:
        logging.error(f"Error enviando plantilla de WhatsApp: {str(e)}")
        raise HTTPException(status_code=500, detail="Error enviando plantilla")
