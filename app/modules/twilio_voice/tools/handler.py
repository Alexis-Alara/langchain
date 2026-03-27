import asyncio
import json
import logging
from datetime import datetime

from fastapi import WebSocket

from app.modules.twilio_voice.prompts.voice import build_voice_instructions
from app.modules.whatsapp.tools.service import whatsapp_service
from app.shared.config.settings import SUPPORT_PHONE, TENANT_ID, TIMEZONE
from app.shared.tools.availability import (
    check_slot_availability,
    format_availability_suggestions,
    get_availability_suggestions,
)
from app.shared.tools.calendar import call_google_calendar
from app.shared.tools.chat_history import get_conversation_history, save_message
from app.shared.tools.leads import create_lead
from app.shared.tools.retrieval import search_semantic
from app.shared.types.call_session import CallSession
from app.shared.utils.documents import join_page_contents

logger = logging.getLogger(__name__)

SILENCE_TIMEOUT_SECONDS = 5

REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "check_availability",
        "description": "Consulta los horarios disponibles para agendar una cita.",
        "parameters": {
            "type": "object",
            "properties": {
                "preferred_date": {
                    "type": "string",
                    "description": "Fecha preferida en formato YYYY-MM-DD.",
                }
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "create_event",
        "description": "Crea una cita cuando ya tienes fecha, hora y correo confirmados.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "startTime": {"type": "string"},
                "title": {"type": "string"},
                "guestEmails": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["date", "startTime", "title", "guestEmails"],
        },
    },
    {
        "type": "function",
        "name": "capture_lead",
        "description": "Guarda datos de un lead cuando el usuario muestra intencion de compra.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "intent_level": {"type": "string", "enum": ["medium", "high"]},
            },
            "required": ["intent_level"],
        },
    },
    {
        "type": "function",
        "name": "search_knowledge",
        "description": "Busca informacion en la base de conocimiento de la empresa.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "escalate_support",
        "description": "Escala la conversacion a un agente humano cuando el usuario lo solicita.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_phone": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["user_phone", "reason"],
        },
    },
]


def build_session_instructions(faiss_context: str, tenant_id: str):
    return build_voice_instructions(faiss_context, tenant_id, timezone=TIMEZONE)


def load_faiss_context(tenant_id: str):
    queries = [
        "informacion general del negocio",
        "horarios ubicacion contacto politicas",
        "preguntas frecuentes soporte dudas",
        "servicios productos precios",
    ]
    documents = []
    seen = set()

    for query in queries:
        for document in search_semantic(query, tenant_id, top_k=8):
            if document.page_content in seen:
                continue
            seen.add(document.page_content)
            documents.append(document)

    return join_page_contents(documents)


async def handle_tool_call(session: CallSession, function_name: str, arguments: dict) -> str:
    tenant_id = session.tenant_id or TENANT_ID

    try:
        if function_name == "check_availability":
            availability_data = get_availability_suggestions(
                preferred_date=arguments.get("preferred_date"),
                tenant_id=tenant_id,
            )
            if availability_data:
                return format_availability_suggestions(availability_data)
            return "No pude consultar los horarios disponibles ahora. Intenta mas tarde."

        if function_name == "create_event":
            event_date = arguments.get("date")
            start_time_iso = arguments.get("startTime", "")
            slot_available = False
            if event_date and start_time_iso:
                try:
                    event_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
                    slot_available = check_slot_availability(
                        event_date,
                        event_dt.strftime("%H:%M"),
                        tenant_id=tenant_id,
                    )
                except Exception as exc:
                    logger.error("Voice slot verification error: %s", str(exc))

            if slot_available:
                event_payload = {**arguments, "tenantId": tenant_id}
                result = call_google_calendar(event_payload)
                create_lead(event_payload)
                if result.get("status") == "success":
                    return "Tu cita quedo registrada. Te enviaremos la confirmacion por correo."
                if result.get("status") == "conflict":
                    alternatives = get_availability_suggestions(
                        preferred_date=event_date,
                        tenant_id=tenant_id,
                    )
                    if alternatives:
                        return f"Ese horario no esta disponible. {format_availability_suggestions(alternatives)}"
                    return "Ese horario no esta disponible. Quieres ver otras opciones?"
                return f"Hubo un problema al registrar la cita: {result.get('message', 'error desconocido')}."

            alternatives = get_availability_suggestions(preferred_date=event_date, tenant_id=tenant_id)
            if alternatives:
                return f"Ese horario no esta disponible. {format_availability_suggestions(alternatives)}"
            return "Ese horario no esta disponible. Por favor dime otra fecha u hora."

        if function_name == "search_knowledge":
            query = arguments.get("query", "")
            if not query:
                return "No recibi ninguna consulta para buscar."
            documents = search_semantic(query, tenant_id)
            if documents:
                return f"Informacion encontrada:\n{join_page_contents(documents)}"
            return "No encontre informacion relevante sobre ese tema en la base de conocimiento."

        if function_name == "capture_lead":
            if arguments.get("name") or arguments.get("email") or arguments.get("phone"):
                create_lead({**arguments, "tenantId": tenant_id})
                return "Listo, ya guarde tus datos. En breve alguien del equipo te contactara."
            return "Necesito al menos tu nombre, correo o telefono para poder ayudarte mejor."

        if function_name == "escalate_support":
            user_phone = arguments.get("user_phone") or session.caller_phone
            reason = arguments.get("reason", "Sin descripcion")

            if not SUPPORT_PHONE:
                logger.error("SUPPORT_PHONE is not configured")
                return "Intente escalar a soporte, pero el numero de soporte no esta configurado."
            if not user_phone:
                return "Para escalar a soporte necesito tu numero de telefono."

            message_to_support = (
                f"[Escalamiento VOZ] Tenant: {tenant_id} | Conversation: {session.conversation_id}\n"
                f"Usuario: {whatsapp_service.format_phone_number(user_phone)}\n"
                f"Motivo: {reason}\n"
            )
            asyncio.create_task(
                whatsapp_service.send_text_message(
                    whatsapp_service.format_phone_number(SUPPORT_PHONE),
                    message_to_support,
                )
            )
            return "He notificado a nuestro equipo de soporte. Un agente te contactara pronto."

        logger.warning("Unknown voice tool: %s", function_name)
        return "No pude ejecutar esa accion."
    except Exception as exc:
        logger.exception("Voice tool error %s: %s", function_name, str(exc))
        return "Ocurrio un error al procesar la accion. Intenta de nuevo."


async def watch_silence(session: CallSession, twilio_ws: WebSocket):
    import time

    await asyncio.sleep(SILENCE_TIMEOUT_SECONDS)
    while True:
        await asyncio.sleep(1)
        if session.last_audio_time is None:
            continue
        elapsed = time.time() - session.last_audio_time
        if elapsed < SILENCE_TIMEOUT_SECONDS:
            continue

        logger.info("Voice silence detected. Closing stream=%s", session.stream_sid)
        try:
            await twilio_ws.send_json({"event": "clear", "streamSid": session.stream_sid})
            await twilio_ws.close()
        except Exception:
            pass
        try:
            if session.openai_ws:
                await session.openai_ws.close()
        except Exception:
            pass
        break


async def listen_openai(session: CallSession, twilio_ws: WebSocket):
    current_assistant_text = ""
    current_function_name = ""
    current_function_args = ""
    current_function_call_id = ""

    async for raw_message in session.openai_ws:
        data = json.loads(raw_message)
        event_type = data.get("type", "")

        if event_type == "response.audio.delta":
            await twilio_ws.send_json(
                {
                    "event": "media",
                    "streamSid": session.stream_sid,
                    "media": {"payload": data["delta"]},
                }
            )
            continue

        if event_type == "response.audio.done":
            await twilio_ws.send_json(
                {
                    "event": "mark",
                    "streamSid": session.stream_sid,
                    "mark": {"name": "end_of_audio"},
                }
            )
            continue

        if event_type == "response.audio_transcript.delta":
            current_assistant_text += data.get("delta", "")
            continue

        if event_type == "response.audio_transcript.done":
            final_text = data.get("transcript", current_assistant_text).strip()
            if final_text:
                save_message(session.tenant_id or TENANT_ID, session.conversation_id, "assistant", final_text)
                logger.info("Voice assistant: %s", final_text[:120])
            current_assistant_text = ""
            continue

        if event_type == "conversation.item.input_audio_transcription.completed":
            user_text = data.get("transcript", "").strip()
            if user_text:
                save_message(session.tenant_id or TENANT_ID, session.conversation_id, "user", user_text)
                logger.info("Voice user: %s", user_text[:120])
            continue

        if event_type == "response.function_call_arguments.delta":
            current_function_args += data.get("delta", "")
            continue

        if event_type == "response.output_item.added":
            item = data.get("item", {})
            if item.get("type") == "function_call":
                current_function_name = item.get("name", "")
                current_function_call_id = item.get("call_id", "")
                current_function_args = ""
            continue

        if event_type == "response.function_call_arguments.done":
            fn_name = data.get("name") or current_function_name
            call_id = data.get("call_id") or current_function_call_id
            raw_args = data.get("arguments") or current_function_args

            try:
                arguments = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                arguments = {}

            result_text = await handle_tool_call(session, fn_name, arguments)
            await session.openai_ws.send(
                json.dumps(
                    {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": result_text,
                        },
                    }
                )
            )
            await session.openai_ws.send(json.dumps({"type": "response.create"}))

            current_function_name = ""
            current_function_call_id = ""
            current_function_args = ""
            continue

        if event_type == "error":
            logger.error("OpenAI realtime error: %s", data)
