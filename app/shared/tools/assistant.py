import asyncio
import json
import logging
import re
from datetime import datetime

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langdetect import detect

from app.modules.whatsapp.tools.service import whatsapp_service
from app.shared.config.settings import AGENT_BASE, AGENT_PROFILE, OPENAI_API_KEY, OPENAI_MODEL, SUPPORT_PHONE, TENANT_ID, TIMEZONE
from app.shared.prompts.assistant import context_prompt
from app.shared.prompts.assistant import system_prompt as _general_system_prompt
from app.shared.prompts.customer_service import specialization_prompt as _customer_service_addon
from app.shared.prompts.custom import system_prompt as _custom_system_prompt
from app.shared.prompts.sales import specialization_prompt as _sales_addon
from app.shared.tools.availability import (
    check_slot_availability,
    format_availability_suggestions,
    get_availability_suggestions,
)
from app.shared.tools.calendar import call_google_calendar
from app.shared.tools.leads import create_lead
from app.shared.tools.retrieval import search_semantic
from app.shared.tools.usage_tracker import save_token_usage

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    model=OPENAI_MODEL,
    temperature=0.2,
)

_PROMPT_TEMPLATE_CACHE: dict[str, PromptTemplate] = {}

_BASE_SYSTEM_PROMPTS: dict[str, str] = {
    "general": _general_system_prompt,
    "custom": _custom_system_prompt,
}

_SPECIALIZATION_ADDONS: dict[str, str] = {
    "sales": _sales_addon,
    "customer_service": _customer_service_addon,
}


def _get_prompt(base: str, profile: str) -> PromptTemplate:
    cache_key = f"{base}:{profile}"
    if cache_key not in _PROMPT_TEMPLATE_CACHE:
        base_system = _BASE_SYSTEM_PROMPTS.get(base, _general_system_prompt)
        addon = _SPECIALIZATION_ADDONS.get(profile, "")
        full_system = base_system + ("\n" + addon if addon else "")
        template = "Fecha y hora actual: {current_date}\n\n" + full_system + "\n" + context_prompt
        _PROMPT_TEMPLATE_CACHE[cache_key] = PromptTemplate(
            input_variables=["context", "query", "language", "tenant_id", "timezone", "current_date"],
            template=template,
        )
    return _PROMPT_TEMPLATE_CACHE[cache_key]


def detect_language(text):
    try:
        return detect(text)
    except Exception:
        return "es"


def _extract_token_usage(response):
    usage_metadata = response.response_metadata if hasattr(response, "response_metadata") else {}
    token_usage = usage_metadata.get("token_usage", {})
    return (
        token_usage.get("prompt_tokens", 0),
        token_usage.get("completion_tokens", 0),
        token_usage.get("total_tokens", 0),
    )


def _dispatch_support_notification(tenant_id: str, conversation_id: str, user_phone: str, reason: str):
    if not SUPPORT_PHONE:
        logger.error("SUPPORT_PHONE is not configured")
        return "Se intento escalar a soporte, pero no esta configurado el numero de soporte."

    if not user_phone:
        return "Para escalar a soporte necesito tu numero de telefono."

    support_formatted = whatsapp_service.format_phone_number(SUPPORT_PHONE)
    user_formatted = whatsapp_service.format_phone_number(user_phone)
    message_to_support = (
        f"[Escalamiento] Tenant: {tenant_id} | Conversation: {conversation_id}\n"
        f"Usuario: {user_formatted}\n"
        f"Motivo: {reason}\n"
    )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(whatsapp_service.send_text_message(support_formatted, message_to_support))
    except RuntimeError:
        asyncio.run(whatsapp_service.send_text_message(support_formatted, message_to_support))

    return "He solicitado el escalamiento a soporte. Un agente te contactara por WhatsApp pronto."


def _handle_action(action_json: dict, question: str, tenant_id: str, conversation_id: str):
    action = action_json.get("action")

    if action == "check_availability":
        preferred_date = action_json.get("preferred_date")
        availability_data = get_availability_suggestions(preferred_date=preferred_date, tenant_id=tenant_id)
        if availability_data:
            return format_availability_suggestions(availability_data)
        return "No pude consultar los horarios disponibles en este momento."

    if action == "capture_lead":
        if action_json.get("name") or action_json.get("email") or action_json.get("phone"):
            create_lead(action_json)
        return action_json.get("response", "")

    if action == "create_event":
        event_date = action_json.get("date")
        start_time_iso = action_json.get("startTime", "")
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
                logger.error("Error verifying create_event slot: %s", str(exc))

        if slot_available:
            result = call_google_calendar(action_json)
            create_lead(action_json)
            if result["status"] == "success":
                return "Tu cita ya quedo registrada."
            if result["status"] == "conflict":
                availability_data = get_availability_suggestions(
                    preferred_date=event_date,
                    tenant_id=tenant_id,
                )
                if availability_data:
                    return (
                        "El horario que propusiste no esta disponible. "
                        f"{format_availability_suggestions(availability_data)}"
                    )
                return "El horario que propusiste no esta disponible."
            return f"Error al crear la cita: {result.get('message', 'Error desconocido')}"

        availability_data = get_availability_suggestions(preferred_date=event_date, tenant_id=tenant_id)
        if availability_data:
            return (
                "El horario que propusiste no esta disponible. "
                f"{format_availability_suggestions(availability_data)}"
            )
        return "El horario que propusiste no esta disponible. Intenta con otro horario."

    if action == "escalate_support":
        user_phone = (
            action_json.get("user_phone")
            or action_json.get("phone")
            or action_json.get("phone_number")
        )
        reason = action_json.get("reason") or action_json.get("summary") or question
        return _dispatch_support_notification(tenant_id, conversation_id, user_phone, reason)

    return None


def generate_answer(
    question: str,
    history=None,
    context: str = "",
    tenant_id: str = None,
    conversation_id: str = None,
    source: str = "web",
    profile: str = None,
):
    tenant_id = tenant_id or TENANT_ID
    base = AGENT_BASE
    profile = profile or AGENT_PROFILE

    if not context:
        documents = search_semantic(question, tenant_id)
        if documents:
            context = "\n".join(document.page_content for document in documents)

    history_text = ""
    if history:
        for message in history:
            prefix = "Usuario:" if message["role"] == "user" else "Asistente:"
            history_text += f"{prefix} {message['content']}\n"

    full_context = history_text
    if context:
        full_context += f"\nContexto de la empresa:\n{context}"

    chain_input = {
        "context": full_context,
        "query": question,
        "language": question,
        "tenant_id": tenant_id,
        "timezone": TIMEZONE,
        "current_date": datetime.now().strftime("%Y-%m-%d (%A)"),
    }
    response = llm.invoke(_get_prompt(base, profile).format(**chain_input))
    response_text = response.content

    prompt_tokens, completion_tokens, total_tokens = _extract_token_usage(response)
    if conversation_id:
        save_token_usage(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            model=OPENAI_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            question=question,
            answer=response_text[:500],
            source=source,
        )

    cleaned = re.sub(r"^```json\n|\n```$", "", response_text.strip(), flags=re.MULTILINE)
    try:
        action_json = json.loads(cleaned)
    except json.JSONDecodeError:
        action_json = {}

    if "action" in action_json:
        action_response = _handle_action(action_json, question, tenant_id, conversation_id)
        if action_response is not None:
            return action_response

    return response_text
