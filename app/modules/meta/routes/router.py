import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app.modules.meta.tools.handler import handle_webhook, verify_webhook
from app.modules.meta.tools.service import meta_messaging_service
from app.shared.config.settings import TENANT_ID
from app.shared.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/meta/webhook")
@router.get("/messenger/webhook")
@router.get("/instagram/webhook")
async def meta_webhook_verification(request: Request):
    verified = await verify_webhook(
        request.query_params.get("hub.mode"),
        request.query_params.get("hub.verify_token"),
        request.query_params.get("hub.challenge"),
    )
    if verified is None:
        raise HTTPException(status_code=403, detail="Token de verificacion invalido")
    return verified


@router.post("/meta/webhook")
@router.post("/messenger/webhook")
@router.post("/instagram/webhook")
@limiter.limit("20/minute")
async def meta_webhook_handler(body: Dict[str, Any], request: Request):
    raw_payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not meta_messaging_service.verify_signature(raw_payload, signature):
        raise HTTPException(status_code=403, detail="Firma de webhook invalida")

    try:
        tenant_id = request.headers.get("tenant_id") or TENANT_ID
        return await handle_webhook(body, tenant_id=tenant_id)
    except Exception as exc:
        logger.error("Error processing Meta webhook: %s", str(exc))
        return {"status": "error", "detail": str(exc)}


@router.get("/meta/diagnostics")
@limiter.limit("10/minute")
async def meta_diagnostics_endpoint(request: Request):
    del request
    try:
        return {"status": "success", "data": meta_messaging_service.get_diagnostics()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error generating Meta diagnostics: %s", str(exc))
        raise HTTPException(status_code=500, detail="Error generando diagnostico de Meta")
