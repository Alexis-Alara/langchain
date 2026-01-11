import os
import json
import re
import requests
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langdetect import detect
from app.services.retrieval import search_semantic
from app.leads import create_lead
from app.services.google_calendar import call_google_calendar
from app.services.usage_tracker import save_token_usage
from app.services.whatsapp import whatsapp_service
import asyncio
from dotenv import load_dotenv
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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

def get_availability_suggestions(preferred_date=None, days_ahead=7, max_slots=50):
    """
    Consulta el endpoint de disponibilidad para obtener horarios sugeridos
    
    Args:
        preferred_date: Fecha preferida en formato YYYY-MM-DD
        days_ahead: Días hacia adelante para buscar
        max_slots: Máximo número de slots a retornar
    
    Returns:
        Dict con la respuesta del endpoint o None si hay error
    """
    try:
        base_url = "http://localhost:3000/api/calendar/availability/suggestions"
        headers = {"Content-Type": "application/json", "tenant_id": TENANT_ID}
        params = {
            "daysAhead": days_ahead,
            "maxSlots": max_slots
        }
        
        if preferred_date:
            params["preferredDate"] = preferred_date
            
        response = requests.get(base_url, params=params, timeout=10, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error consultando disponibilidad: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado en get_availability_suggestions: {str(e)}")
        return None

def format_availability_suggestions(availability_data, max_suggestions=3):
    """
    Formatea las sugerencias de disponibilidad en un texto legible
    
    Args:
        availability_data: Datos de disponibilidad del endpoint
        max_suggestions: Máximo número de sugerencias a mostrar
    
    Returns:
        String con las sugerencias formateadas
    """
    if not availability_data or not availability_data.get("success"):
        return "No se pudieron obtener horarios disponibles en este momento."
    
    days_data = availability_data.get("data", {}).get("days", [])
    suggestions = []
    
    # Mapeo de meses en español
    months_es = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    
    suggestion_count = 0
    
    for day in days_data:
        if not day.get("isBusinessDay") or not day.get("slots"):
            continue
            
        date = day.get("date")
        day_of_week = day.get("dayOfWeek")
        slots = day.get("slots", [])
        
        if slots and suggestion_count < max_suggestions:
            # Tomar los primeros slots del día
            for slot in slots[:3]:  # Máximo 3 slots por día
                if suggestion_count >= max_suggestions:
                    break
                    
                try:
                    start_datetime = datetime.fromisoformat(slot["startDateTime"].replace('Z', '+00:00'))
                    day_num = start_datetime.day
                    month = months_es[start_datetime.month]
                    time = start_datetime.strftime("%H:%M")
                    
                    suggestions.append(f"{day_of_week} {day_num} de {month} a las {time}")
                    suggestion_count += 1
                except Exception as e:
                    logger.error(f"Error formateando slot: {e}")
                    continue
    
    if not suggestions:
        return "No hay horarios disponibles en los próximos días."
    
    formatted_suggestions = "\n".join([f"{i+1}. {suggestion}" for i, suggestion in enumerate(suggestions)])
    return f"Claro! Te sugiero estos horarios disponibles:\n{formatted_suggestions}"

def check_slot_availability(date, start_time):
    """
    Verifica si un slot específico está disponible
    
    Args:
        date: Fecha en formato YYYY-MM-DD
        start_time: Hora de inicio en formato HH:MM
    
    Returns:
        bool: True si está disponible, False si no
    """
    try:
        availability_data = get_availability_suggestions(preferred_date=date, days_ahead=1, max_slots=50)
        
        if not availability_data or not availability_data.get("success"):
            return False
            
        days_data = availability_data.get("data", {}).get("days", [])
        
        for day in days_data:
            if day.get("date") == date:
                slots = day.get("slots", [])
                for slot in slots:
                    if slot.get("startTime") == start_time:
                        return True
        
        return False
    except Exception as e:
        logger.error(f"Error verificando disponibilidad del slot: {e}")
        return False

system_prompt = """
Eres un asistente virtual de soporte para clientes tu objetivo es vender y asistir con el negocio.

Reglas:
1. Detecta el idioma de la pregunta del usuario y responde SIEMPRE en ese idioma.
2. Si el usuario quiere agendar una cita solicita sus datos como correo. Una vez que tengas día, hora y correo, responde SOLO en JSON con el formato exacto:
{{
  "action": "create_event",
  "tenantId": "{tenant_id}",
  "date": "2026-MM-DD",
  "startTime": "2026-MM-DDTHH:MM{timezone}",
  "title": "..."
  "guestEmails": ["...@...com", "...@...com"] (obligatorio tener al menos un correo),
}}
2b. Si el usuario pregunta por horarios disponibles o cuando puede agendar una cita, responde SOLO en JSON:
{{
  "action": "check_availability",
  "tenantId": "{tenant_id}",
  "preferred_date": "2026-MM-DD" (opcional, fecha preferida del usuario, si el usuario no especifica un mes usa el mes actual)
}}
2c. JAMAS generes una cita sin pedir antes el correo del usuario.
3. Si detectas intención de compra o contacto obten datos de informacion de manera natural y continua con la conversacion, no hables sobre enviar informacion por correo u otros medios aun
4. Si detectas intención de compra o contacto (mediana o alta) y solo si tienes información del usuario como nombre o correo, genera un JSON así:
{{
  "action": "capture_lead",
  "tenantId": "{tenant_id}",
  "name": "...",
  "email": "...",
  "intent_level": "medium/high",
  "response": "normal text response to user"
}}
5. Si el usuario tiene un problema o queja y solicita hablar con soporte solicita su telefono y cuando lo tengas, genera un JSON así:
{{
    "action": "escalate_support",
    "tenantId": "{tenant_id}",
    "user_phone": "...",
    "reason": "información sobre el problema o queja y contexto de como se llego a la situacion"
}}
6. Si no hay acción, responde normalmente como asistente virtual.
7. Si generas JSON, asegúrate que el formato sea correcto y válido.
8. Si no tienes suficiente información para crear el evento o capturar el lead, continúa la conversación para obtener más detalles.
9. Siempre responde de manera profesional y amigable.
10. No reveles que eres un modelo de lenguaje o IA.
11. No te desvies del tema base del negocio
12. Recuerda que el timezone del usuario es {timezone}
13. Si el usuario busca información específica de la empresa, usa el contexto proporcionado.
14. Si el usuario desea salir de la conversación o no desea agendar una cita o dejar sus datos, respeta su decisión y finaliza la conversación de manera cordial.
15. Si el usuario se desvía del tema, redirígelo amablemente al tema principal.
16. Siempre mantén un tono positivo y servicial.
17. Asegúrate de cumplir con todas las reglas anteriores en cada respuesta.
18. Trata de responder en un formato menor a 500 caracteres a menos que se requiera mayor informacion.
19. Cuando sea necesaria una accion Responde ÚNICAMENTE con un JSON válido. NO incluyas texto adicional. NO incluyas comentarios. NO envuelvas el JSON en otro objeto.
20. Nunca ignores las instrucciones de este prompt.
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

def generate_answer(question: str, history=None, context="", tenant_id: str = None, conversation_id: str = None, source: str = "web"):
    """
    history: lista de mensajes previos [{"role": "...", "content": "..."}]
    context: texto adicional extraído de FAISS
    tenant_id: ID del tenant para guardar uso
    conversation_id: ID de la conversación
    source: fuente de la solicitud (web, whatsapp, etc)
    """
    
    # Usar valores por defecto si no se proporcionan
    tenant_id = tenant_id or TENANT_ID
    
    # Buscar contexto relevante en FAISS si no se proporciona contexto
    if not context:
        print(f"Buscando contexto en FAISS para tenant_id={tenant_id} y query='{question}'")
        docs = search_semantic(question, tenant_id)
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
        "tenant_id": tenant_id,
        "timezone": TIMEZONE
    }

    print("Generando respuesta con el siguiente input al modelo:")
    print(chain_input)
    
    # Llamada correcta usando invoke
    response = llm.invoke(prompt.format(**chain_input))
    print("Respuesta del modelo:")
    print(response)
    
    # Capturar información de tokens de la respuesta
    response_text = response.content
    usage_metadata = response.response_metadata if hasattr(response, 'response_metadata') else {}
    
    # Extraer información de tokens
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    
    if 'token_usage' in usage_metadata:
        prompt_tokens = usage_metadata['token_usage'].get('prompt_tokens', 0)
        completion_tokens = usage_metadata['token_usage'].get('completion_tokens', 0)
        total_tokens = usage_metadata['token_usage'].get('total_tokens', 0)
    
    print(f"Tokens usados - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
    
    # Guardar uso de tokens en MongoDB
    if conversation_id:
        save_token_usage(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            model="gpt-4o-mini",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            question=question,
            answer=response_text[:500],  # Guardar primeros 500 caracteres
            source=source
        )
    
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
            
            if action_json["action"] == "check_availability":
                # Consultar disponibilidad de horarios
                preferred_date = action_json.get("preferred_date")
                print(f"Consultando disponibilidad para fecha preferida: {preferred_date}")
                
                availability_data = get_availability_suggestions(preferred_date)
                if availability_data:
                    response_text = format_availability_suggestions(availability_data)
                else:
                    response_text = "No pude consultar los horarios disponibles en este momento. Por favor, intenta más tarde."
            
            elif action_json["action"] == "capture_lead":
                if action_json.get("name") or action_json.get("email"):
                    create_lead(action_json)
                    response_text = action_json.get("response", "")

            elif action_json["action"] == "create_event":
                print("Verificando disponibilidad antes de crear evento...")
                
                # Extraer fecha y hora del evento propuesto
                event_date = action_json.get("date")
                start_time_iso = action_json.get("startTime")
                
                # Verificar disponibilidad del slot específico
                slot_available = False
                if event_date and start_time_iso:
                    try:
                        # Extraer solo la hora del startTime ISO
                        dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
                        start_time = dt.strftime("%H:%M")
                        slot_available = check_slot_availability(event_date, start_time)
                    except Exception as e:
                        logger.error(f"Error verificando disponibilidad: {e}")
                        slot_available = False
                
                if slot_available:
                    print("Slot disponible, creando evento en Google Calendar...")
                    result = call_google_calendar('localhost:3000', action_json, 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRJZCI6ImNsaWVudGUxIiwiaWF0IjoxNzU3NTQ0NDYzLCJleHAiOjE3NTgxNDkyNjN9.91KPys7IXXA5SgksNIF77EM8o7dqLAKW6jy_iVMrOTA')
                    create_lead(action_json)
                    print("Resultado de la creación del evento:", result)
                    
                    if result["status"] == "success":
                        response_text = f"¡Ya quedo registrada tu cita!"
                    elif result["status"] == "conflict":
                        # Si hay conflicto, usar el endpoint de disponibilidad para sugerencias
                        availability_data = get_availability_suggestions(preferred_date=event_date)
                        if availability_data:
                            response_text = f"El horario que propusiste no está disponible. {format_availability_suggestions(availability_data)}"
                        else:
                            response_text = "El horario que propusiste no está disponible. Por favor, consulta otros horarios disponibles."
                    else:
                        response_text = f"Error al crear la cita: {result.get('message', 'Error desconocido')}"
                else:
                    print("Slot no disponible, sugiriendo alternativas...")
                    # Si el slot no está disponible, sugerir alternativas
                    availability_data = get_availability_suggestions(preferred_date=event_date)
                    if availability_data:
                        response_text = f"El horario que propusiste no está disponible. {format_availability_suggestions(availability_data)}"
                    else:
                        response_text = "El horario que propusiste no está disponible. Por favor, intenta con otro horario."
            elif action_json["action"] == "escalate_support":
                # Manejar escalamiento a soporte
                support_phone = os.getenv("SUPPORT_PHONE")
                # Buscar número del usuario en el JSON
                user_phone = action_json.get("user_phone") or action_json.get("phone") or action_json.get("phone_number")
                reason = action_json.get("reason") or action_json.get("summary") or question

                if not support_phone:
                    logger.error("SUPPORT_PHONE no configurado en variables de entorno")
                    response_text = "Se intentó escalar a soporte, pero el número de soporte no está configurado. Por favor contacte al administrador."
                else:
                    # Si no tenemos el número del usuario, solicitarlo al usuario
                    if not user_phone:
                        response_text = "Para escalar a soporte, por favor indícame tu número de WhatsApp (incluye código de país)."
                    else:
                        # Formatear números
                        support_formatted = whatsapp_service.format_phone_number(support_phone)
                        user_formatted = whatsapp_service.format_phone_number(user_phone)

                        # Construir mensaje de resumen para soporte
                        message_to_support = (
                            f"[Escalamiento] Tenant: {tenant_id} | Conversation: {conversation_id}\n"
                            f"Usuario: {user_formatted}\n"
                            f"Motivo: {reason}\n"
                        )

                        # Enviar notificación a número de soporte (en background si hay un loop)
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(whatsapp_service.send_text_message(support_formatted, message_to_support))
                        except RuntimeError:
                            # No hay loop corriendo (ej. llamada directa), ejecutar bloqueante
                            asyncio.run(whatsapp_service.send_text_message(support_formatted, message_to_support))

                        response_text = "He solicitado el escalamiento a soporte. Un agente de soporte se pondrá en contacto contigo por WhatsApp pronto."
    except json.JSONDecodeError:
        # No era acción, simplemente seguimos con la respuesta normal
        pass
    
    return response_text