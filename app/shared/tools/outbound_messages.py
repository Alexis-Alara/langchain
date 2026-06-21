from typing import Tuple

from fastapi import HTTPException

from app.modules.meta.tools.service import meta_messaging_service
from app.modules.whatsapp.tools.service import whatsapp_service


def parse_conversation_target(conversation_id: str) -> Tuple[str, str]:
    if "_" not in conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id invalido")

    platform, recipient = conversation_id.split("_", 1)
    normalized_platform = platform.strip().lower()
    recipient = recipient.strip()

    if normalized_platform not in {"whatsapp", "instagram", "messenger"} or not recipient:
        raise HTTPException(status_code=400, detail="conversation_id invalido")

    return normalized_platform, recipient


async def send_message_to_conversation(conversation_id: str, message: str):
    platform, recipient = parse_conversation_target(conversation_id)

    if platform == "whatsapp":
        await whatsapp_service.send_text_message(recipient, message)
        return

    await meta_messaging_service.send_text_message(
        platform=platform,
        recipient_id=recipient,
        message=message,
    )
