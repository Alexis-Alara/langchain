import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.modules.whatsapp.tools.handler import handle_webhook, verify_webhook
from app.shared.config.settings import TENANT_ID
from app.shared.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class WhatsAppContact(BaseModel):
    profile: Dict[str, str]
    wa_id: str


class WhatsAppText(BaseModel):
    body: str


class WhatsAppAudio(BaseModel):
    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    voice: Optional[bool] = None


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(default=None, alias="from")
    id: str
    timestamp: str
    text: Optional[WhatsAppText] = None
    audio: Optional[WhatsAppAudio] = None
    type: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: Dict[str, Any]
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhook(BaseModel):
    object: str
    entry: List[WhatsAppEntry]


@router.get("/whatsapp/webhook")
async def whatsapp_webhook_verification(request: Request):
    challenge = request.query_params.get("hub.challenge")
    verified = await verify_webhook(
        request.query_params.get("hub.mode"),
        request.query_params.get("hub.verify_token"),
        challenge,
    )
    if verified is None:
        raise HTTPException(status_code=403, detail="Token de verificacion invalido")
    return verified


@router.post("/whatsapp/webhook")
@limiter.limit("20/minute")
async def whatsapp_webhook_handler(body: WhatsAppWebhook, request: Request):
    logger.info("WhatsApp webhook received")
    try:
        tenant_id = request.headers.get("tenant_id") or TENANT_ID
        return await handle_webhook(body, tenant_id=tenant_id)
    except Exception as exc:
        logger.error("Error processing WhatsApp webhook: %s", str(exc))
        return {"status": "error", "detail": str(exc)}
