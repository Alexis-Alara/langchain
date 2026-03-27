import logging
from datetime import datetime, timedelta

from app.shared.config.database import usage_collection

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
    source: str = "web",
):
    try:
        usage_doc = {
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "model": model,
            "tokens": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "question": question,
            "answer": answer,
            "source": source,
            "timestamp": datetime.utcnow(),
        }
        result = usage_collection.insert_one(usage_doc)
        logger.info("Token usage saved: %s - total=%s", result.inserted_id, total_tokens)
        return result.inserted_id
    except Exception as exc:
        logger.error("Error saving token usage: %s", str(exc))
        return None


def get_tenant_usage_stats(tenant_id: str, days: int = 30):
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {"tenant_id": tenant_id, "timestamp": {"$gte": cutoff_date}}},
            {
                "$group": {
                    "_id": "$tenant_id",
                    "total_requests": {"$sum": 1},
                    "total_prompt_tokens": {"$sum": "$tokens.prompt_tokens"},
                    "total_completion_tokens": {"$sum": "$tokens.completion_tokens"},
                    "total_tokens": {"$sum": "$tokens.total_tokens"},
                    "average_tokens_per_request": {"$avg": "$tokens.total_tokens"},
                }
            },
        ]
        result = list(usage_collection.aggregate(pipeline))
        return result[0] if result else None
    except Exception as exc:
        logger.error("Error getting tenant usage stats: %s", str(exc))
        return None


def get_conversation_usage(tenant_id: str, conversation_id: str):
    try:
        pipeline = [
            {"$match": {"tenant_id": tenant_id, "conversation_id": conversation_id}},
            {
                "$group": {
                    "_id": "$conversation_id",
                    "messages": {"$sum": 1},
                    "total_prompt_tokens": {"$sum": "$tokens.prompt_tokens"},
                    "total_completion_tokens": {"$sum": "$tokens.completion_tokens"},
                    "total_tokens": {"$sum": "$tokens.total_tokens"},
                }
            },
        ]
        result = list(usage_collection.aggregate(pipeline))
        return result[0] if result else None
    except Exception as exc:
        logger.error("Error getting conversation usage: %s", str(exc))
        return None


def get_usage_by_source(tenant_id: str, days: int = 30):
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        pipeline = [
            {"$match": {"tenant_id": tenant_id, "timestamp": {"$gte": cutoff_date}}},
            {
                "$group": {
                    "_id": "$source",
                    "requests": {"$sum": 1},
                    "total_tokens": {"$sum": "$tokens.total_tokens"},
                    "average_tokens": {"$avg": "$tokens.total_tokens"},
                }
            },
        ]
        return list(usage_collection.aggregate(pipeline))
    except Exception as exc:
        logger.error("Error getting usage by source: %s", str(exc))
        return []
