from dataclasses import dataclass
from typing import Sequence

from fastapi import APIRouter

from app.modules.meta.routes.router import router as meta_router
from app.modules.twilio_voice.routes.router import router as twilio_voice_router
from app.modules.webchat.routes.router import router as webchat_router
from app.modules.whatsapp.routes.router import router as whatsapp_router


@dataclass(frozen=True)
class ModuleRegistration:
    name: str
    description: str
    router: APIRouter
    env_vars: Sequence[str]


REGISTERED_MODULES = (
    ModuleRegistration(
        name="webchat",
        description="Canal web para consulta conversacional",
        router=webchat_router,
        env_vars=("OPENAI_API_KEY", "TENANT_ID"),
    ),
    ModuleRegistration(
        name="whatsapp",
        description="Webhook y salida para WhatsApp Business API",
        router=whatsapp_router,
        env_vars=("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN"),
    ),
    ModuleRegistration(
        name="meta",
        description="Webhook y salida para Messenger e Instagram",
        router=meta_router,
        env_vars=("META_PAGE_ACCESS_TOKEN", "META_VERIFY_TOKEN"),
    ),
    ModuleRegistration(
        name="twilio_voice",
        description="Entrada de voz por Twilio Media Streams y OpenAI Realtime",
        router=twilio_voice_router,
        env_vars=("OPENAI_REALTIME_URL", "TWILIO_MEDIA_STREAM_URL"),
    ),
)
