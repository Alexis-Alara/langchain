import asyncio
import json
import logging

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response

from app.modules.twilio_voice.tools.handler import (
    REALTIME_TOOLS,
    build_session_instructions,
    listen_openai,
    load_faiss_context,
    watch_silence,
)
from app.shared.config.settings import TENANT_ID, TWILIO_MEDIA_STREAM_URL
from app.shared.tools.chat_history import get_conversation_history
from app.shared.tools.realtime_ai import connect_openai
from app.shared.types.call_session import CallSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/twilio/voice")
async def twilio_voice_webhook(request: Request):
    del request
    twiml = f"""
    <Response>
        <Connect>
            <Stream url="{TWILIO_MEDIA_STREAM_URL}" />
        </Connect>
    </Response>
    """
    return Response(content=twiml.strip(), media_type="text/xml")


@router.websocket("/twilio/media-stream")
async def twilio_media_stream(ws: WebSocket):
    await ws.accept()
    session = None

    async for message in ws.iter_text():
        data = json.loads(message)

        if data["event"] == "start":
            stream_sid = data["start"]["streamSid"]
            custom_params = data["start"].get("customParameters", {})
            caller_phone = custom_params.get("caller")
            tenant_id = custom_params.get("tenant_id", TENANT_ID)

            session = CallSession(stream_sid, tenant_id=tenant_id, caller_phone=caller_phone)
            session.openai_ws = await connect_openai()

            faiss_context = load_faiss_context(tenant_id)
            instructions = build_session_instructions(faiss_context, tenant_id)

            history = []
            if caller_phone:
                history = get_conversation_history(tenant_id, session.conversation_id)

            asyncio.create_task(listen_openai(session, ws))
            asyncio.create_task(watch_silence(session, ws))

            await session.openai_ws.send(
                json.dumps(
                    {
                        "type": "session.update",
                        "session": {
                            "turn_detection": {"type": "server_vad"},
                            "input_audio_format": "g711_ulaw",
                            "output_audio_format": "g711_ulaw",
                            "voice": "verse",
                            "instructions": instructions,
                            "tools": REALTIME_TOOLS,
                            "tool_choice": "auto",
                            "input_audio_transcription": {"model": "whisper-1"},
                        },
                    }
                )
            )

            if history:
                for item in list(history)[-10:]:
                    role = "user" if item["role"] == "user" else "assistant"
                    await session.openai_ws.send(
                        json.dumps(
                            {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": role,
                                    "content": [{"type": "input_text", "text": item["content"]}],
                                },
                            }
                        )
                    )

            await session.openai_ws.send(
                json.dumps(
                    {
                        "type": "response.create",
                        "response": {
                            "modalities": ["audio", "text"],
                            "instructions": "Saluda al usuario de forma amigable y breve.",
                        },
                    }
                )
            )
            logger.info("Voice session started stream=%s tenant=%s", stream_sid, tenant_id)
            continue

        if data["event"] == "media" and session and session.openai_ws:
            import time

            session.last_audio_time = time.time()
            await session.openai_ws.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": data["media"]["payload"],
                    }
                )
            )
            continue

        if data["event"] == "stop":
            logger.info("Voice session stopped stream=%s", session.stream_sid if session else "unknown")
            if session and session.openai_ws:
                await session.openai_ws.close()
            break
