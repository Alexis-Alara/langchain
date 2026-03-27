from collections import deque
from datetime import datetime

from app.shared.config.database import chat_history_collection as collection

MAX_HISTORY = 10


def get_conversation_history(tenant_id: str, conversation_id: str):
    document = collection.find_one({"tenantId": tenant_id, "conversation_id": conversation_id})
    if document and "history" in document:
        return deque(document["history"], maxlen=MAX_HISTORY)
    return deque(maxlen=MAX_HISTORY)


def save_message(tenant_id: str, conversation_id: str, role: str, content: str):
    collection.update_one(
        {"tenantId": tenant_id, "conversation_id": conversation_id},
        {
            "$push": {"history": {"role": role, "content": content}},
            "$set": {"updated_at": datetime.utcnow()},
        },
        upsert=True,
    )
