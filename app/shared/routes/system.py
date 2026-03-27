from fastapi import APIRouter

from app.app.registry.modules import REGISTERED_MODULES
from app.shared.config.settings import APP_NAME

router = APIRouter()


@router.get("/")
async def root():
    return {
        "message": APP_NAME,
        "modules": [
            {
                "name": module.name,
                "description": module.description,
                "env_vars": list(module.env_vars),
            }
            for module in REGISTERED_MODULES
        ],
        "endpoints": [
            "/api/query",
            "/api/whatsapp/webhook",
            "/api/meta/webhook",
            "/api/twilio/voice",
            "/health",
        ],
    }


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
