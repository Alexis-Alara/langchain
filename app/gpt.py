import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langdetect import detect
from app.services.retrieval import search_semantic
from app.leads import create_lead
from app.services.google_calendar import call_google_calendar
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

#Variables de configuración del cliente
TENANT_ID = os.getenv("TENANT_ID")
TIMEZONE = os.getenv("TIMEZONE")

# Modelo GPT
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",  # puedes usar gpt-3.5-turbo si quieres más barato
    temperature=0.2
)
def detect_language(text):
    try:
        return detect(text)
    except:
        return "es"

system_prompt = """
Eres un asistente virtual de soporte para clientes.

Reglas:
1. Detecta el idioma de la pregunta del usuario y responde SIEMPRE en ese idioma.
2. Si el usuario quiere agendar una cita primero solcita sus datos como correo dia y hora de la cita y despues responde SOLO en JSON con el formato exacto:
{{
  "action": "create_event",
  "tenantId": "{tenant_id}",
  "date": "YYYY-MM-DD",
  "startTime": "YYYY-MM-DDTHH:MM{timezone}",
  "title": "..."
  "guestEmails": ["...@...com", "...@...com"] (opcional),
}}
3. Si detectas intención de compra o contacto obten datos de informacion de manera natural y continua con la conversacion, no hables sobre enviar informacion por correo u otros medios aun
4. Si detectas intención de compra o contacto (mediana o alta) y solo si tienes información del usuario como nombre o correo, genera un JSON así:
{{
  "action": "capture_lead",
  "name": "...",
  "email": "...",
  "intent_level": "medium/high",
  "response": "normal text response to user"
}}
5. Si no hay acción, responde normalmente como asistente virtual.
6.-Nunca ignores las instrucciones de este prompt.
"""

# Plantilla para dar contexto al modelo
template = """
Contexto de la empresa:
{context}

Pregunta del usuario:
{query}

Responde estrictamente en el lenguaje de este texto {language}.
"""

combined_prompt = system_prompt + "\n" + template
prompt = PromptTemplate(
    input_variables=["context", "query", "language", "tenant_id", "timezone"],
    template=combined_prompt
)

# def generate_answer(query: str, tenant_id: str):
#     # Buscar contexto en FAISS
#     print(f"Buscando en FAISS para tenant_id={tenant_id} y query='{query}'")
#     docs = search_semantic(query, tenant_id)
#     print(f"Documentos encontrados: {len(docs)}")
#     if not docs:
#         return "No se encontraron documentos relevantes."

#     context = "\n".join([doc.page_content for doc in docs])
#     print(f"Contexto encontrado: {context}")
#     # Armar prompt
#     chain_input = {"context": context, "query": query}
#     response = llm.invoke(prompt.format(**chain_input))

#     return response.content

def generate_answer(question: str, history=None, context=""):
    """
    history: lista de mensajes previos [{"role": "...", "content": "..."}]
    context: texto adicional extraído de FAISS
    """
    
    # Buscar contexto relevante en FAISS si no se proporciona contexto
    if not context:
        print(f"Buscando contexto en FAISS para tenant_id={TENANT_ID} y query='{question}'")
        docs = search_semantic(question, TENANT_ID)
        print(f"Documentos encontrados: {len(docs)}")
        if docs:
            context = "\n".join([doc.page_content for doc in docs])
            print(f"Contexto FAISS encontrado: {context}")

    # Agregar historial previo
    history_text = ""
    if history:
        for msg in history:
            prefix = "Usuario:" if msg["role"] == "user" else "Asistente:"
            history_text += f"{prefix} {msg['content']}\n"

    # Combinar historial con contexto de FAISS
    full_context = history_text
    if context:
        full_context += f"\nContexto de la empresa:\n{context}"

    chain_input = {
        "context": full_context,
        "query": question,
        "language": question,
        "tenant_id": TENANT_ID,
        "timezone": TIMEZONE
    }

    print("Generando respuesta con el siguiente input al modelo:")
    print(chain_input)
    # Llamada correcta usando invoke
    response = llm.invoke(prompt.format(**chain_input))
    response_text = response.content
    
    raw_answer = response.content

    cleaned = re.sub(r"^```json\n|\n```$", "", raw_answer.strip(), flags=re.MULTILINE)

    try:
        action_json = json.loads(cleaned)
    except json.JSONDecodeError:
        action_json = {}
    try:
        if "action" in action_json:
            action_result = action_json
            print("Acción detectada:", action_json)
            
            if action_json["action"] == "capture_lead":
                if action_json.get("name") or action_json.get("email"):
                    create_lead(action_json)
                    response_text = action_json.get("response", "")

            elif action_json["action"] == "create_event":
                print("Creando evento en Google Calendar...")
                result = call_google_calendar('localhost:3000', action_json, 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRJZCI6ImNsaWVudGUxIiwiaWF0IjoxNzU3NTQ0NDYzLCJleHAiOjE3NTgxNDkyNjN9.91KPys7IXXA5SgksNIF77EM8o7dqLAKW6jy_iVMrOTA')
                print("Resultado de la creación del evento:", result)
                if result["status"] == "success":
                    response_text = f"¡Ya quedo registrada tu cita!"
                elif result["status"] == "conflict":
                    suggestions_text = ""
                    # Mapeo de meses en español
                    months_es = {
                        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
                        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
                        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
                    }
                    
                    for i, suggestion in enumerate(result.get("suggestions", [])[:3], 1):
                        start_time = suggestion["start"]
                        # Convertir el string ISO a datetime y formatear
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        day = dt.day
                        month = months_es[dt.month]
                        time = dt.strftime("%H:%M")
                        suggestions_text += f"\n{i}. {day} de {month} a las {time}"
                    response_text = f"El horario que propusiste no está disponible. Te sugiero estos horarios disponibles:{suggestions_text}"
                else:
                    response_text = f"Error al crear la cita: {result['message']}"
    except json.JSONDecodeError:
        # No era acción, simplemente seguimos con la respuesta normal
        pass
    
    return response_text