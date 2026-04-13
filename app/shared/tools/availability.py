import json
import logging
from datetime import datetime

import requests

from app.shared.config.settings import API_BASE_URL, TENANT_ID
from app.shared.constants.months import MONTHS_ES

logger = logging.getLogger(__name__)


def _availability_headers(tenant_id=None):
    return {
        "Content-Type": "application/json",
        "tenant_id": tenant_id or TENANT_ID,
    }


def _parse_slot_datetime(slot):
    start_datetime = slot.get("startDateTime")
    if not start_datetime:
        return None
    try:
        return datetime.fromisoformat(start_datetime.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_availability_days(availability_data):
    if not availability_data or not availability_data.get("success"):
        return [], 0

    data = availability_data.get("data", {})
    if data.get("days"):
        total_slots = data.get("totalSlotsAvailable")
        if total_slots is None:
            total_slots = sum(
                day.get("totalSlots", len(day.get("slots", []) or []))
                for day in data.get("days", [])
            )
        return data.get("days", []), total_slots

    if "slots" in data:
        slots = data.get("slots", []) or []
        return [
            {
                "date": data.get("date"),
                "dayOfWeek": data.get("dayOfWeek", ""),
                "isBusinessDay": data.get("isBusinessDay", True),
                "slots": slots,
                "totalSlots": data.get("totalSlots", len(slots)),
            }
        ], data.get("totalSlots", len(slots))

    if "availableSlots" in data:
        slots = data.get("availableSlots", []) or []
        return [
            {
                "date": data.get("date"),
                "dayOfWeek": data.get("dayOfWeek", ""),
                "isBusinessDay": True,
                "slots": slots,
                "totalSlots": data.get("totalSlots", len(slots)),
            }
        ], data.get("totalSlots", len(slots))

    return [], 0


def _build_slot_label(slot, fallback_day_of_week="", fallback_date=None):
    start_datetime = _parse_slot_datetime(slot)
    day_of_week = slot.get("dayOfWeek") or fallback_day_of_week or ""
    if start_datetime:
        date_label = f"{start_datetime.day} de {MONTHS_ES[start_datetime.month]}"
        time_label = start_datetime.strftime("%H:%M")
        prefix = f"{day_of_week} " if day_of_week else ""
        return f"{prefix}{date_label} a las {time_label}"

    start_time = (slot.get("startTime") or "")[:5]
    if fallback_date and start_time:
        try:
            fallback_datetime = datetime.fromisoformat(f"{fallback_date}T{start_time}:00")
            date_label = f"{fallback_datetime.day} de {MONTHS_ES[fallback_datetime.month]}"
            prefix = f"{day_of_week} " if day_of_week else ""
            return f"{prefix}{date_label} a las {start_time}"
        except ValueError:
            pass

    return start_time or "Horario no disponible"


def get_availability_suggestions(preferred_date=None, days_ahead=7, max_slots=50, tenant_id=None):
    try:
        if preferred_date:
            endpoint = "/api/calendar/availability/date"
            params = {"date": preferred_date}
        else:
            endpoint = "/api/calendar/availability/suggestions"
            params = {"daysAhead": days_ahead, "maxSlots": max_slots, "fromDate": datetime.now().strftime("%Y-%m-%d")}

        response = requests.get(
            f"{API_BASE_URL}{endpoint}",
            params=params,
            headers=_availability_headers(tenant_id),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Availability response: %s", json.dumps(data))
        return data
    except requests.RequestException as exc:
        logger.error("Error getting availability: %s", str(exc))
        return None
    except Exception as exc:
        logger.error("Unexpected availability error: %s", str(exc))
        return None


def get_next_available_slot(from_date=None, max_days_ahead=30, tenant_id=None):
    try:
        params = {"maxDaysAhead": max_days_ahead, "fromDate": from_date or datetime.now().strftime("%Y-%m-%d")}

        response = requests.get(
            f"{API_BASE_URL}/api/calendar/availability/next",
            params=params,
            headers=_availability_headers(tenant_id),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Next availability response: %s", json.dumps(data))
        return data
    except requests.RequestException as exc:
        logger.error("Error getting next availability: %s", str(exc))
        return None
    except Exception as exc:
        logger.error("Unexpected next availability error: %s", str(exc))
        return None


def has_available_slots(availability_data):
    days, _ = _normalize_availability_days(availability_data)
    for day in days:
        if not day.get("isBusinessDay", True):
            continue
        if day.get("slots"):
            return True
    return False


def get_next_available_day_suggestions(from_date=None, tenant_id=None):
    next_data = get_next_available_slot(from_date=from_date, tenant_id=tenant_id)
    if not next_data or not next_data.get("success"):
        return None

    next_slot = next_data.get("data", {}).get("nextSlot", {})
    next_date = next_slot.get("date")
    if not next_date:
        return None
    return get_availability_suggestions(preferred_date=next_date, tenant_id=tenant_id)


def format_availability_suggestions(availability_data, max_suggestions=3):
    if not availability_data or not availability_data.get("success"):
        return "No se pudieron obtener horarios disponibles en este momento."

    days, total_slots = _normalize_availability_days(availability_data)
    if not days:
        return "No hay horarios disponibles en este momento."

    suggestions = []
    first_day_reference = None
    for day in days:
        if not day.get("isBusinessDay", True):
            continue
        for slot in day.get("slots", []) or []:
            slot_label = _build_slot_label(slot, day.get("dayOfWeek", ""), day.get("date"))
            if not first_day_reference and " a las " in slot_label:
                first_day_reference = slot_label.split(" a las ")[0]
            suggestions.append(slot_label)
            if len(suggestions) >= max_suggestions:
                break
        if len(suggestions) >= max_suggestions:
            break

    if not suggestions:
        return "No hay horarios disponibles en los proximos dias."

    formatted = "\n".join(
        f"{index + 1}. {suggestion}" for index, suggestion in enumerate(suggestions)
    )

    if len(days) == 1:
        day_total_slots = days[0].get("totalSlots", len(days[0].get("slots", []) or []))
        day_reference = first_day_reference or "ese dia"
        if day_total_slots > len(suggestions):
            intro = (
                f"Para {day_reference} hay {day_total_slots} horarios disponibles. "
                f"Te comparto {len(suggestions)} opciones:"
            )
        else:
            intro = f"Para {day_reference} hay {day_total_slots} horarios disponibles:"
        return f"{intro}\n{formatted}"

    total_slots = total_slots or len(suggestions)
    return (
        f"Tengo {total_slots} horarios disponibles en los proximos dias. "
        f"Te comparto {len(suggestions)} opciones:\n{formatted}"
    )


def check_slot_availability(date, start_time, tenant_id=None):
    availability_data = get_availability_suggestions(
        preferred_date=date,
        days_ahead=1,
        max_slots=50,
        tenant_id=tenant_id,
    )
    if not availability_data or not availability_data.get("success"):
        return False

    days, _ = _normalize_availability_days(availability_data)
    for day in days:
        if day.get("date") != date:
            continue
        for slot in day.get("slots", []) or []:
            candidate = (slot.get("startTime") or "")[:5]
            if candidate == start_time:
                return True
            parsed = _parse_slot_datetime(slot)
            if parsed and parsed.strftime("%H:%M") == start_time:
                return True
    return False


def check_exact_slot_availability(start_datetime, duration=60, tenant_id=None):
    if not start_datetime:
        return False
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/calendar/availability/check",
            params={"startDateTime": start_datetime, "duration": duration},
            headers=_availability_headers(tenant_id),
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return bool(data.get("success") and data.get("data", {}).get("available"))
    except requests.RequestException as exc:
        logger.error("Error checking exact availability: %s", str(exc))
        return False
    except Exception as exc:
        logger.error("Unexpected exact availability error: %s", str(exc))
        return False


def summarize_availability_data(availability_data, preview_slots=8):
    if not availability_data or not availability_data.get("success"):
        return None

    days, total_slots = _normalize_availability_days(availability_data)
    if not days:
        return None

    summarized_days = []
    computed_total_slots = 0
    for day in days:
        day_slots = day.get("slots", []) or []
        day_total_slots = day.get("totalSlots", len(day_slots))
        computed_total_slots += day_total_slots
        preview_labels = []
        day_reference = day.get("date") or "ese dia"

        for slot in day_slots[:preview_slots]:
            slot_label = _build_slot_label(slot, day.get("dayOfWeek", ""), day.get("date"))
            preview_labels.append(slot_label)
            if " a las " in slot_label:
                day_reference = slot_label.split(" a las ")[0]

        summarized_days.append(
            {
                "date": day.get("date"),
                "day_reference": day_reference,
                "is_business_day": bool(day.get("isBusinessDay", True)),
                "total_slots": day_total_slots,
                "preview_slots": preview_labels,
            }
        )

    summary = {
        "success": True,
        "scope": "single_day" if len(summarized_days) == 1 else "multi_day",
        "total_slots": total_slots or computed_total_slots,
        "days": summarized_days,
        "has_more_slots": any(
            day["total_slots"] > len(day["preview_slots"]) for day in summarized_days
        ),
    }
    return json.dumps(summary, ensure_ascii=True, indent=2)
