from datetime import datetime
from .db.mongo import leads_collection as leads_collection

def create_lead(data: dict) -> str:
    if not isinstance(data, dict) or not data:
        raise ValueError("Los datos del lead deben ser un diccionario no vacío")

    data.setdefault("created_at", datetime.utcnow())
    data.setdefault("updated_at", datetime.utcnow())
    data.setdefault("status", "nuevo") 

    result = leads_collection.insert_one(data)
    return str(result.inserted_id)