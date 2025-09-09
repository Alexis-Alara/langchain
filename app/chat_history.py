from datetime import datetime
from .db.mongo import chat_history_collection as collection
from collections import deque

MAX_HISTORY = 10

def get_conversation_history(tenant_id: str, conversation_id: str):
    doc = collection.find_one({"tenant_id": tenant_id, "conversation_id": conversation_id})
    if doc and "history" in doc:
        return deque(doc["history"], maxlen=MAX_HISTORY)
    return deque(maxlen=MAX_HISTORY)

def save_message(tenant_id: str, conversation_id: str, role: str, content: str):
    collection.update_one(
        {"tenant_id": tenant_id, "conversation_id": conversation_id},
        {"$push": {"history": {"role": role, "content": content}},
         "$set": {"updated_at": datetime.utcnow()}},
        upsert=True
    )
