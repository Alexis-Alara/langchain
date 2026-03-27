import io
import logging

from openai import AsyncOpenAI

from app.modules.whatsapp.tools.service import whatsapp_service
from app.shared.config.settings import OPENAI_API_KEY, TENANT_ID
from app.shared.tools.chat_flow import process_text_message

logger = logging.getLogger(__name__)


async def verify_webhook(mode: str, token: str, challenge: str):
    if mode == "subscribe" and token == whatsapp_service.verify_token:
        logger.info("WhatsApp webhook verified")
        return int(challenge)
    return None


async def handle_webhook(body, tenant_id: str = None):
    tenant_id = tenant_id or TENANT_ID
    processed = 0

    for entry in body.entry:
        for change in entry.changes:
            if change.field != "messages":
                continue

            value = change.value
            if not value.messages:
                continue

            for message in value.messages:
                phone_number = whatsapp_service.format_phone_number(message.from_)
                conversation_id = f"whatsapp_{phone_number}"

                if message.type == "text" and message.text:
                    answer = process_text_message(
                        message.text.body,
                        tenant_id,
                        conversation_id,
                        source="whatsapp",
                    )
                    await whatsapp_service.send_text_message(phone_number, answer)
                    processed += 1
                    continue

                if message.type == "audio" and message.audio:
                    try:
                        audio_bytes = await whatsapp_service.download_media(message.audio.id)
                        audio_file = io.BytesIO(audio_bytes)
                        audio_file.name = "audio.ogg"

                        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                        transcript = await client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                        )
                        answer = process_text_message(
                            transcript.text,
                            tenant_id,
                            conversation_id,
                            source="whatsapp",
                        )
                        await whatsapp_service.send_text_message(phone_number, answer)
                        processed += 1
                    except Exception as exc:
                        logger.error("WhatsApp audio processing error: %s", str(exc))
                        await whatsapp_service.send_text_message(
                            phone_number,
                            "No pude procesar tu mensaje de voz. Por favor escribelo.",
                        )

    return {"status": "success", "processed": processed}
