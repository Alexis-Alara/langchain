from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

from app.shared.config.database import chat_history_collection as collection

MAX_HISTORY = 10


def get_conversation_document(tenant_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    return collection.find_one({"tenantId": tenant_id, "conversation_id": conversation_id})


def find_conversation_by_id(conversation_id: str) -> Optional[Dict[str, Any]]:
    return collection.find_one({"conversation_id": conversation_id})


def get_conversation_history(tenant_id: str, conversation_id: str):
    document = get_conversation_document(tenant_id, conversation_id)
    if document and "history" in document:
        return deque(document["history"], maxlen=MAX_HISTORY)
    return deque(maxlen=MAX_HISTORY)


def save_message(tenant_id: str, conversation_id: str, role: str, content: str):
    collection.update_one(
        {"tenantId": tenant_id, "conversation_id": conversation_id},
        {
            "$push": {"history": {"role": role, "content": content, "hour": datetime.utcnow()}},
            "$set": {"tenantId": tenant_id, "updated_at": datetime.utcnow()},
            "$setOnInsert": {"support_active": False},
        },
        upsert=True,
    )


def set_conversation_name(tenant_id: str, conversation_id: str, name: str):
    if not name:
        return

    collection.update_one(
        {"tenantId": tenant_id, "conversation_id": conversation_id},
        {
            "$set": {
                "tenantId": tenant_id,
                "name": name,
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {"history": [], "support_active": False},
        },
        upsert=True,
    )


def is_support_active(tenant_id: str, conversation_id: str) -> bool:
    document = get_conversation_document(tenant_id, conversation_id)
    if not document:
        return False
    return bool(document.get("support_active", False))


def set_support_active(tenant_id: str, conversation_id: str, active: bool):
    collection.update_one(
        {"tenantId": tenant_id, "conversation_id": conversation_id},
        {
            "$set": {
                "tenantId": tenant_id,
                "support_active": active,
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {"history": []},
        },
        upsert=True,
    )
