from pymongo import MongoClient

from app.shared.config.settings import (
    MONGO_CHAT_HISTORY_COLLECTION,
    MONGO_DB,
    MONGO_KNOWLEDGE_COLLECTION,
    MONGO_LEADS_COLLECTION,
    MONGO_URI,
    MONGO_USAGE_COLLECTION,
    validate_database_settings,
)

validate_database_settings()

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
knowledge_collection = db[MONGO_KNOWLEDGE_COLLECTION]
chat_history_collection = db[MONGO_CHAT_HISTORY_COLLECTION]
leads_collection = db[MONGO_LEADS_COLLECTION]
usage_collection = db[MONGO_USAGE_COLLECTION]
