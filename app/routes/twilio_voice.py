from fastapi import WebSocket, APIRouter, Request
from fastapi.responses import Response
import asyncio
import json
import os
import logging
from datetime import datetime
from app.services.audio_utils import decode_mulaw
from app.services.realtime_ai import connect_openai
from app.models.call_session import CallSession
from app.services.retrieval import search_semantic
from app.services.google_calendar import call_google_calendar
from app.leads import create_lead
from app.gpt import (
    get_availability_suggestions,
    format_availability_suggestions,
    check_slot_availability,
    system_prompt,
    TENANT_ID,
    TIMEZONE,
)
from app.chat_history import get_conversation_history, save_message
from app.services.whatsapp import whatsapp_service

logger = logging.getLogger(__name__)
router = APIRouter()
BUSSINESS_RESUME = os.getenv("BUSSINESS_RESUME")
# ---------------------------------------------------------------------------
# Herramientas que el modelo puede invocar durante la llamada de voz
# ---------------------------------------------------------------------------
REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "check_availability",
        "description": (
            "Consulta los horarios disponibles para agendar una cita. "
            "Úsala cuando el usuario pregunte cuándo puede agendar o pida opciones de horario."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "preferred_date": {
                    "type": "string",
                    "description": "Fecha preferida en formato YYYY-MM-DD (opcional).",
                }
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "create_event",
        "description": (
            "Crea una cita en el calendario. "
            "Úsala SOLO cuando tengas fecha, hora Y correo confirmados por el usuario."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Fecha en formato YYYY-MM-DD."},
                "startTime": {
                    "type": "string",
                    "description": "Fecha y hora en formato ISO 8601, ej: 2026-03-10T10:00-06:00.",
                },
                "title": {"type": "string", "description": "Título o motivo de la cita."},
                "guestEmails": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Correos electrónicos de los participantes (al menos uno).",
                },
            },
            "required": ["date", "startTime", "title", "guestEmails"],
        },
    },
    {
        "type": "function",
        "name": "capture_lead",
        "description": (
            "Guarda los datos de un lead cuando el usuario muestra intención de compra. "
            "Úsala en cuanto tengas al menos nombre, email o teléfono."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nombre completo del lead."},
                "email": {"type": "string", "description": "Correo electrónico del lead."},
                "phone": {"type": "string", "description": "Teléfono del lead."},
                "intent_level": {
                    "type": "string",
                    "enum": ["medium", "high"],
                    "description": "Nivel de intención de compra.",
                },
            },
            "required": ["intent_level"],
        },
    },
    {
        "type": "function",
        "name": "search_knowledge",
        "description": (
            "Busca información específica en la base de conocimiento de la empresa. "
            "Úsala cuando el usuario pregunte algo que no está en tu contexto inicial "
            "o necesites información más detallada sobre un tema específico."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Pregunta o tema a buscar en la base de conocimiento.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "escalate_support",
        "description": (
            "Escala la conversación a un agente humano cuando el usuario tiene un problema grave "
            "o solicita hablar con soporte. Requiere el teléfono del usuario."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_phone": {
                    "type": "string",
                    "description": "Número de teléfono del usuario (incluye código de país).",
                },
                "reason": {
                    "type": "string",
                    "description": "Descripción del problema o motivo de escalamiento.",
                },
            },
            "required": ["user_phone", "reason"],
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_voice_instructions(faiss_context: str, tenant_id: str) -> str:
    """Combina el system prompt base con el contexto FAISS para llamadas de voz."""
    voice_addendum = (
        "\n\nINSTRUCCIONES ADICIONALES PARA VOZ:"
        "\n- Estás atendiendo una llamada telefónica. Responde siempre de forma ORAL, "
        "natural y concisa (máximo 2-3 oraciones por turno)."
        "\n- NO uses JSON, listas con viñetas ni formato Markdown en tus respuestas habladas."
        "\n- Cuando necesites ejecutar una acción (capturar lead, crear cita, etc.) "
        "usa las herramientas disponibles en lugar de generar JSON de texto."
        "\n- Si no entiendes algo, pide al usuario que lo repita amablemente."
        "\n- Usa un tono profesional y directo."
        "\n- Evita frases largas."
    )
    context_section = ""
    if faiss_context:
        context_section = f"\n\nCONTEXTO DE LA EMPRESA:\n{faiss_context}\n{BUSSINESS_RESUME}"

    # Fill the placeholders that system_prompt contains
    filled = (
        system_prompt
        .replace("{tenant_id}", tenant_id or "")
        .replace("{timezone}", TIMEZONE or "UTC")
    )
    return filled + context_section + voice_addendum


async def _handle_tool_call(session: CallSession, function_name: str, arguments: dict) -> str:
    """Ejecuta la herramienta solicitada por el modelo y devuelve el resultado en texto."""
    tenant_id = session.tenant_id or TENANT_ID

    try:
        # ------------------------------------------------------------------ #
        if function_name == "check_availability":
            preferred_date = arguments.get("preferred_date")
            logger.info(f"[voice] check_availability preferred_date={preferred_date}")
            availability_data = get_availability_suggestions(preferred_date)
            if availability_data:
                return format_availability_suggestions(availability_data)
            return "No pude consultar los horarios disponibles ahora. Por favor, intenta más tarde."

        # ------------------------------------------------------------------ #
        elif function_name == "create_event":
            event_date = arguments.get("date")
            start_time_iso = arguments.get("startTime", "")
            logger.info(f"[voice] create_event date={event_date} startTime={start_time_iso}")

            # Verify slot availability first
            slot_available = False
            if event_date and start_time_iso:
                try:
                    dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
                    start_time = dt.strftime("%H:%M")
                    slot_available = check_slot_availability(event_date, start_time)
                except Exception as exc:
                    logger.error(f"[voice] Error verificando slot: {exc}")

            if slot_available:
                event_payload = {
                    **arguments,
                    "tenantId": tenant_id,
                }
                result = call_google_calendar("localhost:3000", event_payload)
                create_lead(event_payload)
                logger.info(f"[voice] Resultado evento: {result}")

                if result.get("status") == "success":
                    return "¡Tu cita quedó registrada! Te enviaremos la confirmación por correo."
                elif result.get("status") == "conflict":
                    availability_data = get_availability_suggestions(preferred_date=event_date)
                    if availability_data:
                        return f"Ese horario no está disponible. {format_availability_suggestions(availability_data)}"
                    return "Ese horario no está disponible. ¿Te gustaría ver otras opciones?"
                else:
                    return f"Hubo un problema al registrar la cita: {result.get('message', 'error desconocido')}."
            else:
                availability_data = get_availability_suggestions(preferred_date=event_date)
                if availability_data:
                    return f"Ese horario no está disponible. {format_availability_suggestions(availability_data)}"
                return "Ese horario no está disponible. Por favor dime otra fecha u hora."

        # ------------------------------------------------------------------ #
        elif function_name == "search_knowledge":
            query = arguments.get("query", "")
            logger.info(f"[voice] search_knowledge query={query!r}")
            if not query:
                return "No recibí ninguna consulta para buscar."
            try:
                docs = search_semantic(query, tenant_id)
                if docs:
                    snippets = "\n".join([doc.page_content for doc in docs])
                    return f"Información encontrada:\n{snippets}"
                return "No encontré información relevante sobre ese tema en nuestra base de conocimiento."
            except Exception as exc:
                logger.error(f"[voice] Error en search_knowledge: {exc}")
                return "No pude consultar la base de conocimiento ahora mismo."

        # ------------------------------------------------------------------ #
        elif function_name == "capture_lead":
            logger.info(f"[voice] capture_lead args={arguments}")
            lead_payload = {**arguments, "tenantId": tenant_id}
            if arguments.get("name") or arguments.get("email") or arguments.get("phone"):
                create_lead(lead_payload)
                return "Listo, ya guardé tus datos. En breve alguien de nuestro equipo se pondrá en contacto contigo."
            return "Necesito al menos tu nombre, correo o teléfono para poder ayudarte mejor."

        # ------------------------------------------------------------------ #
        elif function_name == "escalate_support":
            support_phone = os.getenv("SUPPORT_PHONE")
            user_phone = arguments.get("user_phone") or session.caller_phone
            reason = arguments.get("reason", "Sin descripción")
            logger.info(f"[voice] escalate_support user_phone={user_phone}")

            if not support_phone:
                logger.error("[voice] SUPPORT_PHONE no configurado")
                return "Intenté escalar a soporte, pero el número de soporte no está configurado. Por favor contacta al administrador."

            if not user_phone:
                return "Para escalar a soporte necesito tu número de teléfono. ¿Me lo puedes proporcionar?"

            support_formatted = whatsapp_service.format_phone_number(support_phone)
            user_formatted = whatsapp_service.format_phone_number(user_phone)
            message_to_support = (
                f"[Escalamiento VOZ] Tenant: {tenant_id} | Conversation: {session.conversation_id}\n"
                f"Usuario: {user_formatted}\n"
                f"Motivo: {reason}\n"
            )
            asyncio.create_task(
                whatsapp_service.send_text_message(support_formatted, message_to_support)
            )
            return "He notificado a nuestro equipo de soporte. Un agente te contactará pronto."

        # ------------------------------------------------------------------ #
        else:
            logger.warning(f"[voice] Herramienta desconocida: {function_name}")
            return "No pude ejecutar esa acción."

    except Exception as exc:
        logger.exception(f"[voice] Error en _handle_tool_call({function_name}): {exc}")
        return "Ocurrió un error al procesar la acción. Por favor intenta de nuevo."


# ---------------------------------------------------------------------------
# Silence watcher
# ---------------------------------------------------------------------------

SILENCE_TIMEOUT_SECONDS = 5


async def watch_silence(session: CallSession, twilio_ws: WebSocket):
    """Cierra la llamada si el usuario no envía audio durante SILENCE_TIMEOUT_SECONDS."""
    import time
    await asyncio.sleep(SILENCE_TIMEOUT_SECONDS)  # grace period before monitoring starts
    while True:
        await asyncio.sleep(1)
        if session.last_audio_time is None:
            continue
        elapsed = time.time() - session.last_audio_time
        if elapsed >= SILENCE_TIMEOUT_SECONDS:
            logger.info(
                f"[voice] Silencio de {elapsed:.1f}s detectado. Cerrando llamada "
                f"stream_sid={session.stream_sid}"
            )
            try:
                # Tell Twilio to hang up
                hangup_twiml = "<Response><Hangup/></Response>"
                await twilio_ws.send_json({
                    "event": "clear",
                    "streamSid": session.stream_sid,
                })
                await twilio_ws.close()
            except Exception:
                pass
            try:
                if session.openai_ws:
                    await session.openai_ws.close()
            except Exception:
                pass
            break


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/twilio/voice")
async def twilio_voice_webhook(request: Request):

    twiml = """
    <Response>
        <Connect>
            <Stream url="wss://unconvened-unmindfully-xander.ngrok-free.dev/api/twilio/media-stream" />
        </Connect>
    </Response>
    """
    return Response(content=twiml.strip(), media_type="text/xml")


@router.websocket("/twilio/media-stream")
async def twilio_media_stream(ws: WebSocket):
    await ws.accept()
    session: CallSession = None

    async for message in ws.iter_text():
        data = json.loads(message)

        # ------------------------------------------------------------------ #
        if data["event"] == "start":
            stream_sid = data["start"]["streamSid"]
            custom_params = data["start"].get("customParameters", {})
            caller_phone = custom_params.get("caller", None)
            tenant_id = custom_params.get("tenant_id", TENANT_ID)

            session = CallSession(stream_sid, tenant_id=tenant_id, caller_phone=caller_phone)
            session.openai_ws = await connect_openai()

            # Load FAISS context with a generic greeting query
            try:
                queries = [
                    "información general del negocio",
                    "horarios ubicación contacto políticas",
                    "preguntas frecuentes soporte dudas",
                    "servicios productos precios"
                ]
                all_docs = []
                seen = set()
                for q in queries:
                    docs = search_semantic(q, tenant_id, top_k=8)
                    for doc in (docs or []):
                        if doc.page_content not in seen:
                            seen.add(doc.page_content)
                            all_docs.append(doc)
                faiss_context = "\n".join([doc.page_content for doc in all_docs]) if all_docs else ""
            except Exception:
                faiss_context = ""

            instructions = _build_voice_instructions(faiss_context, tenant_id)

            # Retrieve previous conversation history if caller is known
            history = []
            if caller_phone:
                history = get_conversation_history(tenant_id, session.conversation_id)

            # Start listening to OpenAI and silence watcher as background tasks
            asyncio.create_task(listen_openai(session, ws))
            asyncio.create_task(watch_silence(session, ws))

            # Configure the Realtime session with tools and system instructions
            await session.openai_ws.send(json.dumps({
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
            }))

            # Inject prior chat history as context messages
            if history:
                for msg in history[-10:]:  # last 10 turns to avoid token overflow
                    role = "user" if msg["role"] == "user" else "assistant"
                    await session.openai_ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": role,
                            "content": [{"type": "input_text", "text": msg["content"]}],
                        },
                    }))

            # Initial greeting
            await session.openai_ws.send(json.dumps({
                "type": "response.create",
                "response": {
                    "modalities": ["audio", "text"],
                    "instructions": "Saluda al usuario de forma amigable y breve.",
                },
            }))

            logger.info(
                f"[voice] Sesión iniciada stream_sid={stream_sid} tenant={tenant_id} caller={caller_phone}"
            )

        # ------------------------------------------------------------------ #
        elif data["event"] == "media":
            if session and session.openai_ws:
                import time
                session.last_audio_time = time.time()
                await session.openai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": data["media"]["payload"],
                }))

        # ------------------------------------------------------------------ #
        elif data["event"] == "stop":
            logger.info(f"[voice] Llamada finalizada stream_sid={session.stream_sid if session else 'unknown'}")
            if session and session.openai_ws:
                await session.openai_ws.close()
            break


# ---------------------------------------------------------------------------
# OpenAI Realtime listener
# ---------------------------------------------------------------------------

async def listen_openai(session: CallSession, twilio_ws: WebSocket):
    """Escucha los eventos del WebSocket de OpenAI Realtime y los maneja."""

    # Buffers para reconstruir el texto hablado y las llamadas a funciones
    current_assistant_text = ""
    current_user_text = ""
    current_function_name = ""
    current_function_args = ""
    current_function_call_id = ""

    async for raw_message in session.openai_ws:
        data = json.loads(raw_message)
        event_type = data.get("type", "")

        # ------------------------------------------------------------------ #
        # Audio delta → forward to Twilio
        if event_type == "response.audio.delta":
            await twilio_ws.send_json({
                "event": "media",
                "streamSid": session.stream_sid,
                "media": {"payload": data["delta"]},
            })

        # ------------------------------------------------------------------ #
        # Audio done → send mark
        elif event_type == "response.audio.done":
            await twilio_ws.send_json({
                "event": "mark",
                "streamSid": session.stream_sid,
                "mark": {"name": "end_of_audio"},
            })

        # ------------------------------------------------------------------ #
        # Accumulate assistant text transcript (for history)
        elif event_type == "response.audio_transcript.delta":
            current_assistant_text += data.get("delta", "")

        elif event_type == "response.audio_transcript.done":
            final_text = data.get("transcript", current_assistant_text).strip()
            if final_text:
                save_message(session.tenant_id or TENANT_ID, session.conversation_id, "assistant", final_text)
                logger.info(f"[voice] Asistente: {final_text[:120]}")
            current_assistant_text = ""

        # ------------------------------------------------------------------ #
        # Accumulate user transcript (speech-to-text)
        elif event_type == "conversation.item.input_audio_transcription.completed":
            user_text = data.get("transcript", "").strip()
            if user_text:
                save_message(session.tenant_id or TENANT_ID, session.conversation_id, "user", user_text)
                logger.info(f"[voice] Usuario: {user_text[:120]}")

        # ------------------------------------------------------------------ #
        # Function call accumulation
        elif event_type == "response.function_call_arguments.delta":
            current_function_args += data.get("delta", "")

        elif event_type == "response.output_item.added":
            item = data.get("item", {})
            if item.get("type") == "function_call":
                current_function_name = item.get("name", "")
                current_function_call_id = item.get("call_id", "")
                current_function_args = ""
                logger.info(f"[voice] Función invocada: {current_function_name}")

        # ------------------------------------------------------------------ #
        # Function call complete → execute and return result
        elif event_type == "response.function_call_arguments.done":
            fn_name = data.get("name") or current_function_name
            call_id = data.get("call_id") or current_function_call_id
            raw_args = data.get("arguments") or current_function_args

            try:
                arguments = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                arguments = {}

            logger.info(f"[voice] Ejecutando {fn_name} args={arguments}")
            result_text = await _handle_tool_call(session, fn_name, arguments)
            logger.info(f"[voice] Resultado {fn_name}: {result_text[:120]}")

            # Return result to the model
            await session.openai_ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result_text,
                },
            }))

            # Ask the model to continue responding based on the tool result
            await session.openai_ws.send(json.dumps({"type": "response.create"}))

            # Reset buffers
            current_function_name = ""
            current_function_call_id = ""
            current_function_args = ""

        # ------------------------------------------------------------------ #
        elif event_type == "error":
            logger.error(f"[voice] Error OpenAI Realtime: {data}")

        else:
            logger.debug(f"[voice] Evento ignorado: {event_type}")