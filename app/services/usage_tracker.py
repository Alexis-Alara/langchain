"""
Servicio para rastrear y guardar el uso de tokens y recursos
"""
from datetime import datetime
from app.db.mongo import usage_collection
import logging

logger = logging.getLogger(__name__)

def save_token_usage(
    tenant_id: str,
    conversation_id: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    question: str = None,
    answer: str = None,
    source: str = "web"
):
    """
    Guarda el uso de tokens en MongoDB
    
    Args:
        tenant_id (str): ID del tenant
        conversation_id (str): ID de la conversación
        model (str): Nombre del modelo usado (ej: gpt-4o-mini)
        prompt_tokens (int): Tokens usados en el prompt
        completion_tokens (int): Tokens usados en la respuesta
        total_tokens (int): Total de tokens
        question (str, optional): La pregunta del usuario
        answer (str, optional): La respuesta del agente
        source (str, optional): Fuente de la solicitud (web, whatsapp, etc)
    """
    try:
        usage_doc = {
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "model": model,
            "tokens": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "question": question,
            "answer": answer,
            "source": source,
            "timestamp": datetime.utcnow()
        }
        
        result = usage_collection.insert_one(usage_doc)
        logger.info(f"Token usage guardado: {result.inserted_id} - Tokens totales: {total_tokens}")
        return result.inserted_id
    
    except Exception as e:
        logger.error(f"Error guardando token usage: {str(e)}")
        return None

def get_tenant_usage_stats(tenant_id: str, days: int = 30):
    """
    Obtiene estadísticas de uso de un tenant en los últimos N días
    
    Args:
        tenant_id (str): ID del tenant
        days (int): Cantidad de días atrás a consultar
    
    Returns:
        dict: Estadísticas de uso
    """
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "timestamp": {"$gte": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": "$tenant_id",
                    "total_requests": {"$sum": 1},
                    "total_prompt_tokens": {"$sum": "$tokens.prompt_tokens"},
                    "total_completion_tokens": {"$sum": "$tokens.completion_tokens"},
                    "total_tokens": {"$sum": "$tokens.total_tokens"},
                    "average_tokens_per_request": {"$avg": "$tokens.total_tokens"}
                }
            }
        ]
        
        result = list(usage_collection.aggregate(pipeline))
        return result[0] if result else None
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return None

def get_conversation_usage(tenant_id: str, conversation_id: str):
    """
    Obtiene el uso de tokens de una conversación específica
    
    Args:
        tenant_id (str): ID del tenant
        conversation_id (str): ID de la conversación
    
    Returns:
        dict: Resumen de uso de la conversación
    """
    try:
        pipeline = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "conversation_id": conversation_id
                }
            },
            {
                "$group": {
                    "_id": "$conversation_id",
                    "messages": {"$sum": 1},
                    "total_prompt_tokens": {"$sum": "$tokens.prompt_tokens"},
                    "total_completion_tokens": {"$sum": "$tokens.completion_tokens"},
                    "total_tokens": {"$sum": "$tokens.total_tokens"}
                }
            }
        ]
        
        result = list(usage_collection.aggregate(pipeline))
        return result[0] if result else None
    
    except Exception as e:
        logger.error(f"Error obteniendo uso de conversación: {str(e)}")
        return None

def get_usage_by_source(tenant_id: str, days: int = 30):
    """
    Obtiene el uso de tokens por fuente (web, whatsapp, etc)
    
    Args:
        tenant_id (str): ID del tenant
        days (int): Cantidad de días atrás a consultar
    
    Returns:
        list: Uso por fuente
    """
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "timestamp": {"$gte": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": "$source",
                    "requests": {"$sum": 1},
                    "total_tokens": {"$sum": "$tokens.total_tokens"},
                    "average_tokens": {"$avg": "$tokens.total_tokens"}
                }
            }
        ]
        
        result = list(usage_collection.aggregate(pipeline))
        return result
    
    except Exception as e:
        logger.error(f"Error obteniendo uso por fuente: {str(e)}")
        return []
