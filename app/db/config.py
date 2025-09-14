import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_KNOWLEDGE_COLLECTION = os.getenv("MONGO_KNOWLEDGE_COLLECTION")
MONGO_CHAT_HISTORY_COLLECTION = os.getenv("MONGO_CHAT_HISTORY_COLLECTION")
MONGO_LEADS_COLLECTION = os.getenv("MONGO_LEADS_COLLECTION")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([MONGO_URI, MONGO_DB, MONGO_KNOWLEDGE_COLLECTION, MONGO_CHAT_HISTORY_COLLECTION, MONGO_LEADS_COLLECTION, OPENAI_API_KEY]):
    raise ValueError("One or more environment variables are missing in the .env file.")