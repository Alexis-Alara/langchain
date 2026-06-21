from typing import Optional, Tuple

from fastapi import HTTPException

from app.shared.tools.chat_history import (
    find_conversation_by_id,
    get_conversation_document,
    save_message,
    set_support_active,
)
from app.shared.tools.outbound_messages import send_message_to_conversation


def resolve_conversation(conversation_id: str, tenant_id: Optional[str]) -> Tuple[str, dict]:
    resolved_tenant_id = tenant_id
    conversation = None

    if resolved_tenant_id:
        conversation = get_conversation_document(resolved_tenant_id, conversation_id)
    else:
        conversation = find_conversation_by_id(conversation_id)
        if conversation:
            resolved_tenant_id = conversation.get("tenantId")

    if not resolved_tenant_id or not conversation:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada")

    return resolved_tenant_id, conversation


async def send_support_message(conversation_id: str, response: str, tenant_id: Optional[str]):
    resolved_tenant_id, _ = resolve_conversation(conversation_id, tenant_id)

    await send_message_to_conversation(conversation_id, response)
    set_support_active(resolved_tenant_id, conversation_id, True)
    save_message(resolved_tenant_id, conversation_id, "support", response)

    return {
        "status": "success",
        "conversation_id": conversation_id,
        "tenant_id": resolved_tenant_id,
        "support_active": True,
    }


def close_support_conversation(conversation_id: str, tenant_id: Optional[str]):
    resolved_tenant_id, _ = resolve_conversation(conversation_id, tenant_id)
    set_support_active(resolved_tenant_id, conversation_id, False)

    return {
        "status": "success",
        "conversation_id": conversation_id,
        "tenant_id": resolved_tenant_id,
        "support_active": False,
    }
