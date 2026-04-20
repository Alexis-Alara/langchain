import os

from dotenv import load_dotenv

load_dotenv()


def get_env(*names: str, default=None):
    for name in names:
        value = os.getenv(name)
        if value not in (None, ""):
            return value
    return default


APP_NAME = "Impulso Chatbot API"
APP_DESCRIPTION = "API para chatbot con integraciones modulares"
APP_VERSION = "1.0.0"
ENABLED_MODULES = get_env("ENABLED_MODULES", default="all")

OPENAI_API_KEY = get_env("OPENAI_API_KEY")
OPENAI_MODEL = get_env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_REALTIME_URL = get_env("OPENAI_REALTIME_URL")

TENANT_ID = get_env("TENANT_ID", default="default")
TIMEZONE = get_env("TIMEZONE", default="America/Mexico_City")
API_BASE_URL = get_env("API_BASE_URL", default="http://localhost:3000")
FAISS_PATH = get_env("FAISS_PATH", default="faiss_index")

MONGO_URI = get_env("MONGO_URI", "MONGODB_URI")
MONGO_DB = get_env("MONGO_DB", "MONGODB_DATABASE")
MONGO_KNOWLEDGE_COLLECTION = get_env("MONGO_KNOWLEDGE_COLLECTION", default="knowledge")
MONGO_CHAT_HISTORY_COLLECTION = get_env("MONGO_CHAT_HISTORY_COLLECTION", default="chat_history")
MONGO_LEADS_COLLECTION = get_env("MONGO_LEADS_COLLECTION", default="leads")
MONGO_USAGE_COLLECTION = get_env("MONGO_USAGE_COLLECTION", default="usage")

WHATSAPP_ACCESS_TOKEN = get_env("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = get_env("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = get_env("WHATSAPP_VERIFY_TOKEN", default="IMPULSO_VERIFY_TOKEN")
WHATSAPP_GRAPH_VERSION = get_env("WHATSAPP_GRAPH_VERSION", default="v17.0")

META_PAGE_ID = get_env("META_PAGE_ID", default="")
META_PAGE_ACCESS_TOKEN = get_env("META_PAGE_ACCESS_TOKEN", default="")
META_IG_BUSINESS_ID = get_env("META_IG_BUSINESS_ID", default="")
INSTAGRAM_ACCESS_TOKEN = get_env("INSTAGRAM_ACCESS_TOKEN", default="")
META_VERIFY_TOKEN = get_env("META_VERIFY_TOKEN", default="IMPULSO_META_VERIFY_TOKEN")
META_APP_SECRET = get_env("META_APP_SECRET", default="")
META_GRAPH_VERSION = get_env("META_GRAPH_VERSION", default="v21.0")

SUPPORT_PHONE = get_env("SUPPORT_PHONE", default="")
BUSINESS_RESUME = get_env("BUSINESS_RESUME", "BUSSINESS_RESUME", default="")
# Base del prompt del agente: "general" | "custom"
AGENT_BASE = get_env("AGENT_BASE", default="general")
# Especializacion sobre la base: "sales" | "customer_service" | "" (ninguna)
AGENT_PROFILE = get_env("AGENT_PROFILE", default="")
TWILIO_MEDIA_STREAM_URL = get_env(
    "TWILIO_MEDIA_STREAM_URL",
    default="wss://unconvened-unmindfully-xander.ngrok-free.dev/api/twilio/media-stream",
)


def validate_database_settings():
    required = {
        "MONGO_URI or MONGODB_URI": MONGO_URI,
        "MONGO_DB or MONGODB_DATABASE": MONGO_DB,
        "OPENAI_API_KEY": OPENAI_API_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
