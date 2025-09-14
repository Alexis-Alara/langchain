from pymongo import MongoClient
from app.db.config import MONGO_URI, MONGO_DB, MONGO_KNOWLEDGE_COLLECTION, MONGO_CHAT_HISTORY_COLLECTION, MONGO_LEADS_COLLECTION

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
knowledge_collection = db[MONGO_KNOWLEDGE_COLLECTION]
chat_history_collection = db[MONGO_CHAT_HISTORY_COLLECTION]
leads_collection = db[MONGO_LEADS_COLLECTION]
