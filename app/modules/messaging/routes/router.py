from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.modules.messaging.tools.auth import require_messaging_token
from app.modules.messaging.tools.handler import close_support_conversation, send_support_message

router = APIRouter()


class SupportMessageRequest(BaseModel):
    conversation_id: str
    response: str


class CloseSupportRequest(BaseModel):
    conversation_id: str


@router.post("/messages")
async def create_support_message(body: SupportMessageRequest, request: Request):
    require_messaging_token(request)
    tenant_id = request.headers.get("tenant_id") or request.headers.get("tenant-id")
    return await send_support_message(body.conversation_id, body.response, tenant_id)


@router.post("/messages/close")
async def close_support_message(body: CloseSupportRequest, request: Request):
    require_messaging_token(request)
    tenant_id = request.headers.get("tenant_id") or request.headers.get("tenant-id")
    return close_support_conversation(body.conversation_id, tenant_id)
