import logging

from app.leads import create_lead
from app.services.google_calendar import call_google_calendar

from .availability import (
    check_exact_slot_availability,
    get_availability_suggestions,
    get_next_available_day_suggestions,
    has_available_slots,
)
from .responses import generate_human_availability_response

logger = logging.getLogger(__name__)

CALENDAR_ROUTE = "localhost:3000"
CALENDAR_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ0ZW5hbnRJZCI6ImNsaWVudGUxIiwiaWF0IjoxNzU3NTQ0NDYzLCJleHAiOjE3NTgxNDkyNjN9."
    "91KPys7IXXA5SgksNIF77EM8o7dqLAKW6jy_iVMrOTA"
)


def _handle_check_availability(action_json, question, history_text, tenant_id):
    preferred_date = action_json.get("preferred_date")
    print(f"Consultando disponibilidad para fecha preferida: {preferred_date}")

    availability_data = get_availability_suggestions(preferred_date, tenant_id=tenant_id)
    if not availability_data:
        return "No pude consultar los horarios disponibles en este momento. Por favor, intenta mas tarde."

    if has_available_slots(availability_data):
        return generate_human_availability_response(
            question=question,
            history_text=history_text,
            availability_data=availability_data,
            sales_context=(
                "El usuario esta preguntando por disponibilidad o validando si existen mas "
                "horarios aparte de los que ya vio. Debes responder con claridad, sonar humano "
                "y guiarlo a elegir una opcion."
            ),
        )

    next_available_data = get_next_available_day_suggestions(
        from_date=preferred_date,
        tenant_id=tenant_id,
    )
    if next_available_data and has_available_slots(next_available_data):
        return generate_human_availability_response(
            question=question,
            history_text=history_text,
            availability_data=next_available_data,
            sales_context=(
                "La fecha inicial que se consulto ya no tiene espacios disponibles. Debes decirlo con "
                "claridad y ofrecer la siguiente fecha disponible con opciones concretas."
            ),
        )

    return "En este momento no veo espacios disponibles en los proximos dias. Si quieres, lo vuelvo a revisar en un momento."


def _build_conflict_response(question, history_text, event_date, tenant_id, sales_context):
    availability_data = get_availability_suggestions(preferred_date=event_date, tenant_id=tenant_id)
    if availability_data and has_available_slots(availability_data):
        return generate_human_availability_response(
            question=question,
            history_text=history_text,
            availability_data=availability_data,
            sales_context=sales_context,
        )

    next_available_data = get_next_available_day_suggestions(
        from_date=event_date,
        tenant_id=tenant_id,
    )
    if next_available_data and has_available_slots(next_available_data):
        return generate_human_availability_response(
            question=question,
            history_text=history_text,
            availability_data=next_available_data,
            sales_context=(
                "El horario o el dia que pidio el usuario ya no tiene espacios disponibles. Debes decirlo "
                "con tacto y ofrecer la siguiente fecha disponible con opciones claras."
            ),
        )

    if not availability_data:
        return "El horario que propusiste no esta disponible. Por favor, intenta con otro horario."

    return "En este momento no veo espacios disponibles en los proximos dias. Si quieres, lo vuelvo a revisar en un momento."


def _handle_create_event(action_json, question, history_text, tenant_id):
    print("Verificando disponibilidad antes de crear evento...")

    event_date = action_json.get("date")
    start_time_iso = action_json.get("startTime")

    slot_available = False
    if event_date and start_time_iso:
        try:
            slot_available = check_exact_slot_availability(
                start_time_iso,
                duration=action_json.get("duration", 60),
                tenant_id=tenant_id,
            )
        except Exception as exc:
            logger.error("Error verificando disponibilidad: %s", str(exc))
            slot_available = False

    if slot_available:
        print("Slot disponible, creando evento en Google Calendar...")
        result = call_google_calendar(CALENDAR_ROUTE, action_json, CALENDAR_TOKEN)
        create_lead(action_json)
        print("Resultado de la creación del evento:", result)

        if result["status"] == "success":
            return "Listo, tu cita ya quedo registrada. Si quieres, tambien puedo ayudarte con cualquier duda antes de tu reunion."

        if result["status"] == "conflict":
            return _build_conflict_response(
                question=question,
                history_text=history_text,
                event_date=event_date,
                tenant_id=tenant_id,
                sales_context=(
                    "El horario exacto que pidio el usuario ya no esta disponible. Debes decirlo "
                    "con tacto, ofrecer alternativas cercanas y mantener un tono comercial."
                ),
            )

        if result["status"] == "limit_reached":
            return result.get(
                "message",
                "Ya registraste una cita hoy desde esta misma conexion. Si necesitas otra, intenta nuevamente manana.",
            )

        return f"Error al crear la cita: {result.get('message', 'Error desconocido')}"

    print("Slot no disponible, sugiriendo alternativas...")
    return _build_conflict_response(
        question=question,
        history_text=history_text,
        event_date=event_date,
        tenant_id=tenant_id,
        sales_context=(
            "El horario que pidio el usuario no esta disponible. Debes explicarlo con claridad, "
            "mostrar alternativas y ayudarlo a avanzar hacia una reserva."
        ),
    )


def handle_calendar_action(action_json, question, history_text, tenant_id):
    action = action_json.get("action")

    if action == "check_availability":
        return _handle_check_availability(action_json, question, history_text, tenant_id)

    if action == "create_event":
        return _handle_create_event(action_json, question, history_text, tenant_id)

    return None
