from datetime import datetime
from .db.mongo import leads_collection as leads_collection

def create_lead(data: dict) -> str:
    if not isinstance(data, dict) or not data:
        raise ValueError("Los datos del lead deben ser un diccionario no vacío")

    if(data.get("guestEmails")):
        data["email"] = data["guestEmails"][0]
        del data["guestEmails"]
    if(data.get("intent_level")):
        data["intent_level"] = "medium/high"
    if not data.get("name"):
        data["name"] = "Desconocido"
    if not data.get("response"):
        data["response"] = "Cita agendada correctamente."
    if not data.get("date"):
        data["date"] = datetime.utcnow().date().isoformat()
    if data.get("startTime"):
        del data["startTime"]
    
        
    data.setdefault("created_at", datetime.utcnow())
    data.setdefault("updated_at", datetime.utcnow())
    data.setdefault("status", "nuevo") 

    result = leads_collection.insert_one(data)
    return str(result.inserted_id)