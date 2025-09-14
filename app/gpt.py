import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langdetect import detect
from app.services.retrieval import search_semantic
from app.leads import create_lead
from app.services.google_calendar import call_google_calendar
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
2. Si el usuario quiere agendar una cita, responde SOLO en JSON con el formato exacto:
{{
  "action": "create_event",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "title": "...",
  "description": "..."
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
    input_variables=["context", "query", "language"],
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

    # Agregar historial previo
    history_text = ""
    if history:
        for msg in history:
            prefix = "Usuario:" if msg["role"] == "user" else "Asistente:"
            history_text += f"{prefix} {msg['content']}\n"

    # Combinar historial con contexto
    full_context = history_text
    if context:
        full_context += f"\nContexto relevante:\n{context}"

    chain_input = {
        "context": full_context,
        "query": question,
        "language": question
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
                response_text = f"Cita creada correctamente: {result.get('status')}"

    except json.JSONDecodeError:
        # No era acción, simplemente seguimos con la respuesta normal
        pass
    
    return response_text