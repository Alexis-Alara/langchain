from datetime import datetime

from app.shared.config.database import leads_collection


def create_lead(data: dict) -> str:
    if not isinstance(data, dict) or not data:
        raise ValueError("Lead data must be a non-empty dictionary")

    payload = dict(data)

    if payload.get("guestEmails"):
        payload["email"] = payload["guestEmails"][0]
        del payload["guestEmails"]
    if payload.get("intent_level"):
        payload["intent_level"] = "medium/high"
    if not payload.get("name"):
        payload["name"] = "Desconocido"
    if not payload.get("response"):
        payload["response"] = "Cita agendada correctamente."
    if not payload.get("date"):
        payload["date"] = datetime.utcnow().date().isoformat()
    if payload.get("startTime"):
        del payload["startTime"]

    payload.setdefault("created_at", datetime.utcnow())
    payload.setdefault("updated_at", datetime.utcnow())
    payload.setdefault("status", "nuevo")

    result = leads_collection.insert_one(payload)
    return str(result.inserted_id)
