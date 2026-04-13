from dataclasses import dataclass
from importlib import import_module
from typing import Sequence

from app.shared.config.settings import ENABLED_MODULES


@dataclass(frozen=True)
class ModuleRegistration:
    name: str
    description: str
    router_import: str
    env_vars: Sequence[str]

    def load_router(self):
        module_name, attr_name = self.router_import.split(":")
        module = import_module(module_name)
        return getattr(module, attr_name)


ALL_MODULES = (
    ModuleRegistration(
        name="webchat",
        description="Canal web para consulta conversacional",
        router_import="app.modules.webchat.routes.router:router",
        env_vars=("OPENAI_API_KEY", "TENANT_ID"),
    ),
    ModuleRegistration(
        name="whatsapp",
        description="Webhook y salida para WhatsApp Business API",
        router_import="app.modules.whatsapp.routes.router:router",
        env_vars=("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN"),
    ),
    ModuleRegistration(
        name="meta",
        description="Webhook y salida para Messenger e Instagram",
        router_import="app.modules.meta.routes.router:router",
        env_vars=("META_PAGE_ACCESS_TOKEN", "META_VERIFY_TOKEN"),
    ),
    ModuleRegistration(
        name="twilio_voice",
        description="Entrada de voz por Twilio Media Streams y OpenAI Realtime",
        router_import="app.modules.twilio_voice.routes.router:router",
        env_vars=("OPENAI_REALTIME_URL", "TWILIO_MEDIA_STREAM_URL"),
    ),
)

MODULES_BY_NAME = {module.name: module for module in ALL_MODULES}

COMMON_ENV_SECTIONS = (
    (
        "Modules",
        (
            ("ENABLED_MODULES", "all"),
        ),
    ),
    (
        "OpenAI",
        (
            ("OPENAI_API_KEY", "tu_openai_api_key_aqui"),
            ("OPENAI_MODEL", "gpt-4o-mini"),
        ),
    ),
    (
        "App",
        (
            ("TENANT_ID", "default"),
            ("TIMEZONE", "America/Mexico_City"),
            ("API_BASE_URL", "http://localhost:3000"),
            ("FAISS_PATH", "faiss_index"),
            ("SUPPORT_PHONE", "+5215551234567"),
            ("BUSINESS_RESUME", "Resumen corto del negocio"),
        ),
    ),
    (
        "MongoDB",
        (
            ("MONGO_URI", "mongodb://localhost:27017"),
            ("MONGO_DB", "impulso_chatbot"),
            ("MONGO_KNOWLEDGE_COLLECTION", "knowledge"),
            ("MONGO_CHAT_HISTORY_COLLECTION", "chat_history"),
            ("MONGO_LEADS_COLLECTION", "leads"),
            ("MONGO_USAGE_COLLECTION", "usage"),
        ),
    ),
)

MODULE_ENV_SECTIONS = {
    "webchat": (),
    "whatsapp": (
        (
            "WhatsApp Business API",
            (
                ("WHATSAPP_ACCESS_TOKEN", "tu_whatsapp_access_token_aqui"),
                ("WHATSAPP_PHONE_NUMBER_ID", "tu_phone_number_id_aqui"),
                ("WHATSAPP_VERIFY_TOKEN", "IMPULSO_VERIFY_TOKEN"),
                ("WHATSAPP_GRAPH_VERSION", "v17.0"),
            ),
        ),
    ),
    "meta": (
        (
            "Meta Messaging",
            (
                ("META_PAGE_ID", "tu_meta_page_id"),
                ("META_PAGE_ACCESS_TOKEN", "tu_meta_page_access_token"),
                ("META_IG_BUSINESS_ID", "tu_instagram_business_id"),
                ("INSTAGRAM_ACCESS_TOKEN", "tu_instagram_access_token"),
                ("META_VERIFY_TOKEN", "IMPULSO_META_VERIFY_TOKEN"),
                ("META_APP_SECRET", "tu_meta_app_secret"),
                ("META_GRAPH_VERSION", "v21.0"),
            ),
        ),
    ),
    "twilio_voice": (
        (
            "Twilio Voice",
            (
                ("OPENAI_REALTIME_URL", "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"),
                ("TWILIO_MEDIA_STREAM_URL", "wss://tu-dominio.dev/api/twilio/media-stream"),
            ),
        ),
    ),
}


def normalize_module_names(requested=None):
    raw_requested = ENABLED_MODULES if requested is None else requested

    if isinstance(raw_requested, str):
        cleaned = raw_requested.strip()
        if not cleaned or cleaned.lower() == "all":
            return tuple(module.name for module in ALL_MODULES)
        module_names = [item.strip() for item in cleaned.split(",") if item.strip()]
    else:
        module_names = [str(item).strip() for item in raw_requested if str(item).strip()]

    unique_names = []
    for name in module_names:
        if name not in MODULES_BY_NAME:
            valid_names = ", ".join(MODULES_BY_NAME.keys())
            raise ValueError(f"Unknown module '{name}'. Valid values: {valid_names}")
        if name not in unique_names:
            unique_names.append(name)

    return tuple(unique_names)


def get_registered_modules(requested=None):
    return tuple(MODULES_BY_NAME[name] for name in normalize_module_names(requested))


REGISTERED_MODULES = get_registered_modules()
