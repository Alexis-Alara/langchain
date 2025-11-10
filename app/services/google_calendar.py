import requests
import os
from datetime import datetime, timedelta

def call_google_calendar(route: str, event_data: dict, token: str = None):
    """
    Convierte los datos mínimos en un evento y lo envía a la API interna.
    """
    base_url = os.getenv("API_BASE_URL", "http://localhost:3000")
    
    payload = {
        "tenantId": event_data.get("tenantId"),
        "title": event_data["title"],
        "startTime": event_data["startTime"],
        "guestEmails": event_data.get("guestEmails", [])
    }

    url = f"{base_url}/api/calendar/appointments"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code in (200, 201):
        response_data = response.json()
        
        # Handle success response
        if response_data.get("success") is True:
            return {
                "status": "success",
                "message": response_data.get("message", "Appointment created successfully"),
                "appointmentId": response_data.get("appointmentId"),
                "googleEventId": response_data.get("googleEventId")
            }
        
        # Handle time conflict with suggestions
        elif response_data.get("success") is False and "suggestions" in response_data:
            return {
                "status": "conflict",
                "message": response_data.get("message", "El horario que propusiste ya está ocupado. Aquí tienes algunas sugerencias:"),
                "suggestions": response_data.get("suggestions", [])
            }
        
        # Handle other errors
        elif "error" in response_data:
            return {
                "status": "error",
                "message": "Ya has creado una cita hoy. Por favor, intenta nuevamente mañana."
            }
    
    # Handle HTTP errors
    return {
        "status": "error",
        "message": f"Ya has creado una cita hoy. Por favor, intenta nuevamente mañana."
    }
