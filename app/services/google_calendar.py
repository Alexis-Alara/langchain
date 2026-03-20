import json
import os

import requests


def _safe_json_response(response):
    try:
        return response.json()
    except ValueError:
        return {}


def _extract_suggestions(response_data):
    if not isinstance(response_data, dict):
        return []

    suggestions = response_data.get("suggestions")
    if isinstance(suggestions, list):
        return suggestions

    error_payload = response_data.get("error")
    if isinstance(error_payload, dict):
        nested_suggestions = error_payload.get("suggestions")
        if isinstance(nested_suggestions, list):
            return nested_suggestions

    if isinstance(error_payload, str):
        try:
            parsed_error = json.loads(error_payload)
        except json.JSONDecodeError:
            return []

        if isinstance(parsed_error, list):
            return parsed_error

        if isinstance(parsed_error, dict):
            nested_suggestions = parsed_error.get("suggestions")
            if isinstance(nested_suggestions, list):
                return nested_suggestions

    return []


def call_google_calendar(route: str, event_data: dict, token: str = None):
    """
    Convierte los datos minimos en un evento y lo envia a la API interna.
    """
    base_url = os.getenv("API_BASE_URL", "http://localhost:3000")

    payload = {
        "title": event_data["title"],
        "startTime": event_data["startTime"],
        "guestEmails": event_data.get("guestEmails", [])
    }

    if event_data.get("description"):
        payload["description"] = event_data["description"]

    if event_data.get("duration"):
        payload["duration"] = event_data["duration"]

    url = f"{base_url}/api/calendar/appointments"
    headers = {"Content-Type": "application/json", "tenant_id": event_data.get("tenantId")}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
    except requests.RequestException as exc:
        return {
            "status": "error",
            "message": f"No se pudo crear la cita en este momento: {str(exc)}"
        }

    response_data = _safe_json_response(response)
    response_payload = response_data.get("data", {}) if isinstance(response_data.get("data"), dict) else {}
    response_message = response_data.get("message") or response_data.get("error")
    suggestions = _extract_suggestions(response_data)

    if response.status_code in (200, 201) and response_data.get("success") is True:
        return {
            "status": "success",
            "message": response_data.get("message", "Appointment created successfully"),
            "appointmentId": response_payload.get("appointmentId") or response_data.get("appointmentId"),
            "googleEventId": response_payload.get("googleEventId") or response_data.get("googleEventId")
        }

    if suggestions:
        return {
            "status": "conflict",
            "message": response_message or "El horario que propusiste ya no esta disponible.",
            "suggestions": suggestions
        }

    if response.status_code == 409:
        return {
            "status": "limit_reached",
            "message": response_message or "Ya registraste una cita hoy desde esta misma conexion. Intenta nuevamente manana."
        }

    return {
        "status": "error",
        "message": response_message or f"No se pudo crear la cita. Codigo HTTP: {response.status_code}"
    }
