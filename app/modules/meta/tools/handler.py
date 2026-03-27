import logging
from typing import Any, Dict

from app.modules.meta.tools.service import meta_messaging_service
from app.shared.config.settings import TENANT_ID
from app.shared.tools.chat_flow import process_text_message

logger = logging.getLogger(__name__)


async def verify_webhook(mode: str, token: str, challenge: str):
    if mode == "subscribe" and token == meta_messaging_service.verify_token:
        logger.info("Meta webhook verified")
        return int(challenge)
    return None


async def handle_webhook(body: Dict[str, Any], tenant_id: str = None):
    object_type = str(body.get("object", "")).lower()
    if object_type not in ("page", "instagram"):
        return {"status": "ignored", "reason": "unsupported_object"}

    tenant_id = tenant_id or TENANT_ID
    source = "instagram" if object_type == "instagram" else "messenger"
    processed = 0

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            message = event.get("message")
            if not sender_id or not message or message.get("is_echo"):
                continue

            message_text = message.get("text")
            if not message_text:
                continue

            conversation_id = f"{source}_{sender_id}"
            answer = process_text_message(
                message_text,
                tenant_id,
                conversation_id,
                source=source,
            )
            await meta_messaging_service.send_text_message(
                platform=source,
                recipient_id=sender_id,
                message=answer,
            )
            processed += 1

    return {"status": "success", "processed": processed}
