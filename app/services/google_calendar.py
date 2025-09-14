import requests
from datetime import datetime, timedelta

def call_google_calendar(route: str, event_data: dict, token: str = None):
    """
    Convierte los datos mínimos en un evento y lo envía a la API interna.
    """
    # Construir datetime inicial
    start_dt = datetime.strptime(f"{event_data['date']} {event_data['time']}", "%Y-%m-%d %H:%M")
    # Por defecto el evento dura 1 hora
    end_dt = start_dt + timedelta(hours=1)

    payload = {
        "calendarId": "primary",
        "summary": event_data["title"],
        "description": event_data.get("description", ""),
        "start": start_dt.isoformat() + "-06:00",  # Ajusta tu zona horaria aquí
        "end": end_dt.isoformat() + "-06:00"
    }

    url = f"http://localhost:3000/api/calendar/events"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code in (200, 201):
        return response.json()
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")
