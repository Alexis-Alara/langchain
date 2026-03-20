import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langdetect import detect
from app.services.retrieval import search_semantic
from app.leads import create_lead
from app.services.appointments.actions import handle_calendar_action
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
TIMEZONE = os.getenv("TIMEZONE") or "America/Mexico_City"

# Modelo GPT
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",  # puedes usar gpt-3.5-turbo si quieres más barato
    temperature=0.2
)

GENERIC_BUSINESS_INTENT_PATTERNS = [
    r"\bmi negocio\b",
    r"\bmi empresa\b",
    r"\btu negocio\b",
    r"\btu empresa\b",
    r"\bcomo puedes ayudarme\b",
    r"\bcomo me puedes ayudar\b",
    r"\ben que me puedes ayudar\b",
    r"\bque puedes hacer por mi\b",
    r"\bque servicios\b",
    r"\bque ofreces\b",
    r"\bcomo funciona\b",
    r"\bsoluciones\b",
    r"\bautomatiza",
    r"\bagente(s)? de ia\b",
    r"\bpagina(s)? web\b",
    r"\bcita(s)?\b",
    r"\bprecio(s)?\b",
    r"\bservicio(s)?\b",
    r"\bcon tu servicio\b",
    r"\bcon sus servicio(s)?\b",
    r"\bcomo podri(a|á)s mejorar\b",
    r"\bcomo mejorari(a|á)s\b",
    r"\bcomo me ayudari(a|á)s\b",
    r"\bcomo ayudari(a|á)s a mi negocio\b",
    r"\bcomo aplicari(a|á)s\b",
    r"\bcomo usari(a|á)\b",
    r"\bcomo lo usaria\b",
    r"\bme serviria\b",
    r"\bme servir(i|í)a\b",
    r"\bme ayudaria\b",
    r"\bme ayudari(a|á)\b",
    r"\bmis consultas\b",
    r"\bmis clientes\b",
    r"\bmis prospectos\b",
    r"\bmis ventas\b",
    r"\bmis citas\b",
    r"\bsoy un\b",
    r"\bsoy una\b",
    r"\btengo una\b",
    r"\btengo un\b",
    r"\bconsultorio\b",
    r"\bclinica\b",
    r"\bdespacho\b",
]

CONSULTATIVE_SERVICE_PATTERNS = [
    r"\bque agente\b",
    r"\bqué agente\b",
    r"\bagente puedo usar\b",
    r"\bque plan\b",
    r"\bqué plan\b",
    r"\bque servicio\b",
    r"\bqué servicio\b",
    r"\bque solucion\b",
    r"\bqué solución\b",
    r"\bcomo me ayudaria\b",
    r"\bcómo me ayudaría\b",
    r"\bcomo aplicaria\b",
    r"\bcómo aplicaría\b",
    r"\bcomo usaria\b",
    r"\bcómo usaría\b",
    r"\bme recomiendas\b",
    r"\bpuedo usar\b",
]

APPLICATION_CONTEXT_PATTERNS = [
    r"\bpara mi\b",
    r"\ben mi\b",
    r"\bpara un\b",
    r"\bpara una\b",
    r"\bmi puesto\b",
    r"\bmi local\b",
    r"\bmi tienda\b",
    r"\bmi negocio\b",
    r"\bmi empresa\b",
    r"\bmi restaurante\b",
    r"\bmi consultorio\b",
    r"\bmi clinica\b",
    r"\bmi clínica\b",
]

OUT_OF_SCOPE_PATTERNS = [
    r"\btacos?\b",
    r"\bpizza\b",
    r"\bhamburguesa",
    r"\bcomida\b",
    r"\brestaurante\b",
    r"\bnetflix\b",
    r"\bpelicula(s)?\b",
    r"\bcancion(es)?\b",
    r"\bvideojuego(s)?\b",
    r"\bfutbol\b",
]

URL_PATTERN = re.compile(r"https?://[^\s]+")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
PHONE_PATTERN = re.compile(r"\+?\d[\d\-\s\(\)]{7,}\d")

LINK_STOPWORDS = {
    "a", "al", "algo", "como", "con", "cual", "cuales", "de", "del", "donde",
    "el", "ella", "ellas", "ellos", "en", "es", "esta", "este", "esto", "hay",
    "la", "las", "le", "les", "lo", "los", "me", "mi", "mis", "necesita",
    "necesito", "no", "para", "pero", "por", "puede", "puedo", "que", "quiero",
    "se", "si", "su", "sus", "te", "tu", "tus", "un", "una", "uno", "y",
}

EXPLICIT_LINK_REQUEST_PATTERNS = [
    r"\blink\b",
    r"\burl\b",
    r"\benlace\b",
    r"\bliga\b",
    r"\bpagina\b",
    r"\bsitio web\b",
    r"\bformulario\b",
    r"\bdonde lo veo\b",
    r"\bdonde puedo verlo\b",
    r"\bdonde contrato\b",
]

PLAN_DISCOVERY_PATTERNS = [
    r"\bno se que plan\b",
    r"\bno sé qué plan\b",
    r"\bque plan necesito\b",
    r"\bqué plan necesito\b",
    r"\bcual plan\b",
    r"\bcu[aá]l plan\b",
    r"\bayudame a elegir\b",
    r"\bayudame a decidir\b",
    r"\bme ayudas a elegir\b",
]

PURCHASE_CLOSING_PATTERNS = [
    r"\bquiero comprar\b",
    r"\bquiero contratar\b",
    r"\bquiero comprarte\b",
    r"\bme interesa contratar\b",
    r"\bquiero el plan\b",
    r"\bme quedo con\b",
    r"\bquiero avanzar\b",
]

CONTACT_MESSAGE_WORDS = {
    "mi", "correo", "email", "mail", "es", "telefono", "teléfono", "cel",
    "celular", "whatsapp", "numero", "número", "contacto",
}


def _matches_any_pattern(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)


def _normalize_link_tokens(text):
    tokens = re.findall(r"[a-zA-Z0-9áéíóúñü]+", (text or "").lower())
    return [token for token in tokens if len(token) >= 3 and token not in LINK_STOPWORDS]


def _contains_only_contact_words(text):
    words = re.findall(r"[a-zA-Záéíóúñü]+", (text or "").lower())
    return bool(words) and all(word in CONTACT_MESSAGE_WORDS for word in words)


def is_contact_payload(text):
    normalized_text = (text or "").strip().lower()
    if not normalized_text:
        return False

    if EMAIL_PATTERN.fullmatch(normalized_text):
        return True

    if PHONE_PATTERN.fullmatch(normalized_text):
        return True

    if EMAIL_PATTERN.search(normalized_text):
        text_without_email = EMAIL_PATTERN.sub(" ", normalized_text)
        if not text_without_email.strip() or _contains_only_contact_words(text_without_email):
            return True

    if PHONE_PATTERN.search(normalized_text):
        text_without_phone = PHONE_PATTERN.sub(" ", normalized_text)
        if not text_without_phone.strip() or _contains_only_contact_words(text_without_phone):
            return True

    return False

def detect_language(text):
    try:
        return detect(text)
    except:
        return "es"


def build_history_text(history, max_messages=8):
    if not history:
        return "Sin historial previo relevante."

    try:
        history_items = list(history)
    except TypeError:
        history_items = [history]

    lines = []
    for msg in history_items[-max_messages:]:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        prefix = "Usuario" if role == "user" else "Asistente"
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{prefix}: {content}")

    return "\n".join(lines) if lines else "Sin historial previo relevante."


def sanitize_history_for_contact_payload(history):
    if not history:
        return history

    sanitized = []
    try:
        history_items = list(history)
    except TypeError:
        history_items = [history]

    for msg in history_items:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        if role == "assistant" and (URL_PATTERN.search(content) or re.search(r"\b(link|enlace|url)\b", content, re.IGNORECASE)):
            continue

        sanitized.append({"role": role, "content": content})

    return sanitized


scope_guard_prompt = PromptTemplate(
    input_variables=["business_context", "history", "question"],
    template="""
Eres un filtro de alcance para un asistente comercial.

Tu tarea es decidir si la pregunta del usuario esta dentro del tema del negocio.

Debes ser permisivo con preguntas consultivas y comerciales.

Marca `in_scope: true` si la pregunta:
- trata sobre productos, servicios, precios, promociones, sucursales, horarios, citas, contacto, soporte o informacion del negocio
- pregunta de forma general como puedes ayudar, que ofreces, como funciona tu servicio o como apoyas a su negocio
- explica el contexto del cliente para entender como aplicaria el servicio en su caso, por ejemplo su giro, profesion, clinica, despacho, negocio, consultas, clientes o procesos
- o es una continuacion clara de una conversacion activa sobre el negocio

Marca `in_scope: false` si la pregunta:
- pide comida, recomendaciones, entretenimiento, cultura general o cualquier tema no relacionado con el negocio
- cambia a un tema distinto al negocio
- es claramente ajena al negocio y no intenta relacionarla con el servicio

Responde UNICAMENTE con JSON valido:
{{
  "in_scope": true,
  "reason": "short reason"
}}

Contexto del negocio:
{business_context}

Historial reciente:
{history}

Pregunta del usuario:
{question}
"""
)




def is_consultative_business_question(normalized_question):
    has_service_signal = _matches_any_pattern(normalized_question, CONSULTATIVE_SERVICE_PATTERNS)
    has_application_context = _matches_any_pattern(normalized_question, APPLICATION_CONTEXT_PATTERNS)
    return has_service_signal and has_application_context


def is_business_scope_question(question, history_text="", business_context=""):
    normalized_question = (question or "").strip().lower()
    if normalized_question:
        has_business_signal = _matches_any_pattern(normalized_question, GENERIC_BUSINESS_INTENT_PATTERNS)
        has_clear_out_of_scope_signal = _matches_any_pattern(normalized_question, OUT_OF_SCOPE_PATTERNS)
        has_consultative_business_signal = is_consultative_business_question(normalized_question)

        if has_business_signal or has_consultative_business_signal:
            return True

        if has_clear_out_of_scope_signal:
            return False

        # Si ya hay contexto del negocio o historial y la pregunta no es claramente ajena,
        # preferimos permitirla para no romper conversaciones consultivas.
        if (history_text and history_text != "Sin historial reciente.") or business_context:
            return True

    try:
        response = llm.invoke(
            scope_guard_prompt.format(
                business_context=business_context or "Sin contexto disponible del negocio.",
                history=history_text or "Sin historial reciente.",
                question=question
            )
        )
        content = (response.content or "").strip()
        cleaned = re.sub(r"^```json\s*|\s*```$", "", content, flags=re.MULTILINE)
        parsed = json.loads(cleaned)
        return bool(parsed.get("in_scope", True))
    except Exception as e:
        logger.error(f"Error evaluando alcance del negocio: {e}")
        return True


def extract_relevant_links(question, context, max_links=2):
    if not context:
        return []

    query_tokens = set(_normalize_link_tokens(question))
    ranked_links = {}

    for line in str(context).splitlines():
        urls = URL_PATTERN.findall(line)
        if not urls:
            continue

        normalized_line = line.lower()
        score = 2 if urls else 0

        if query_tokens:
            for token in query_tokens:
                if re.search(rf"\b{re.escape(token)}\b", normalized_line):
                    score += 3
                elif token in normalized_line:
                    score += 1

        if any(keyword in normalized_line for keyword in ("link", "url", "formulario", "onboarding", "plan", "registro")):
            score += 3

        if score <= 2:
            continue

        for url in urls:
            current = ranked_links.get(url)
            if current is None or score > current["score"]:
                ranked_links[url] = {"url": url, "score": score, "line": line.strip()}

    ordered_links = sorted(
        ranked_links.values(),
        key=lambda item: item["score"],
        reverse=True,
    )
    return ordered_links[:max_links]


def append_relevant_link(answer, question, links):
    clean_answer = (answer or "").strip()
    if not clean_answer or not links:
        return clean_answer

    if is_contact_payload(question):
        return clean_answer

    primary_link = links[0]
    primary_url = primary_link.get("url", "")
    primary_line = (primary_link.get("line") or "").lower()
    normalized_question = (question or "").lower()
    normalized_answer = clean_answer.lower()

    if primary_url in clean_answer:
        return clean_answer

    explicit_link_request = _matches_any_pattern(normalized_question, EXPLICIT_LINK_REQUEST_PATTERNS)
    plan_discovery_intent = _matches_any_pattern(normalized_question, PLAN_DISCOVERY_PATTERNS)
    purchase_closing_intent = _matches_any_pattern(normalized_question, PURCHASE_CLOSING_PATTERNS)
    answer_is_closing = any(
        phrase in normalized_answer
        for phrase in (
            "necesitare tu correo",
            "necesitaré tu correo",
            "me lo puedes proporcionar",
            "me lo puedes compartir",
            "pasame tu correo",
            "pásame tu correo",
            "comparteme tu correo",
            "compárteme tu correo",
        )
    )

    if purchase_closing_intent and not explicit_link_request and not plan_discovery_intent:
        return clean_answer

    if answer_is_closing and not explicit_link_request and "formulario" not in primary_line:
        return clean_answer

    language = detect_language(question or clean_answer)
    separator = "" if clean_answer.endswith((".", "!", "?")) else "."

    if language.startswith("en"):
        if explicit_link_request:
            connector = "Here is the link:"
        elif "formulario" in primary_line or "registro" in primary_line or "onboarding" in primary_line:
            connector = "If you want to continue from here, use this form:"
        elif plan_discovery_intent:
            connector = "This link will help you compare the best option for you:"
        else:
            connector = "Here is the relevant link:"
    else:
        if explicit_link_request:
            connector = "Aqui tienes el link:"
        elif "formulario" in primary_line or "registro" in primary_line or "onboarding" in primary_line:
            connector = "Si quieres avanzar desde aqui, este es el formulario:"
        elif plan_discovery_intent:
            connector = "Este link te ayuda a ubicar la mejor opcion para ti:"
        else:
            connector = "Aqui tienes el link:"

    return f"{clean_answer}{separator} {connector} {primary_url}"


def build_out_of_scope_response(question):
    language = detect_language(question or "")
    if language.startswith("en"):
        return "I can only help with questions about the business, such as services, pricing, availability, appointments, or support. If you want, ask me something about that."

    return "Solo puedo ayudarte con informacion del negocio, como servicios, precios, horarios, citas o soporte. Si quieres, te ayudo con eso."

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
4. Si detectas intención de compra o contacto (mediana o alta) y solo si tienes información del usuario como nombre, correo o telefono, genera un JSON así:
{{
  "action": "capture_lead",
  "tenantId": "{tenant_id}",
  "name": "..." (obligatorio al menos nombre, email o telefono),
  "email": "..." (obligatorio al menos nombre, email o telefono),
  "phone": "..." (obligatorio al menos nombre, email o telefono),
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

system_prompt = """
Eres el asesor comercial y de atencion del negocio. Debes sonar como una persona real: cercana, segura, profesional, resolutiva y natural. Tu objetivo es ayudar al usuario, generar confianza y mover la conversacion hacia una cita o un lead cuando tenga sentido.

Estilo obligatorio en respuestas normales:
1. Responde primero la duda exacta del usuario.
2. Suena humano, conversacional y natural. Evita frases roboticas, repetitivas o demasiado genericas.
3. Habla como un vendedor consultivo: detecta interes, resalta valor, resuelve objeciones y guia el siguiente paso sin presionar.
4. Se explicito. Si hay condiciones, limites, opciones adicionales o pasos pendientes, dilo claramente.
5. Cuando hables de horarios, aclara si estas mostrando solo algunas opciones o todas las disponibles.
6. Cierra con una pregunta breve o una invitacion clara cuando ayude a avanzar la conversacion.
7. Mantente breve: idealmente menos de 500 caracteres, salvo que el usuario pida detalle.
8. Detecta el idioma del usuario y responde SIEMPRE en ese idioma.
9. No reveles que eres un modelo de lenguaje o IA.
10. No te desvies del tema base del negocio.
11. Si el usuario pregunta por algo fuera del negocio, no respondas el contenido de ese tema. Indica brevemente que solo puedes ayudar con temas del negocio y redirige la conversacion.
12. Usa el contexto proporcionado cuando el usuario pida informacion especifica de la empresa.
13. Si el contexto contiene un link o URL que resuelve la duda del usuario, compartelo tal cual y explica en una frase para que sirve. No inventes links.
14. Si el usuario solo comparte datos de contacto como correo o telefono, no metas links en la respuesta a menos que el usuario los pida explicitamente.
15. Respeta al usuario si no desea agendar, comprar o dejar sus datos.
16. Recuerda que el timezone del usuario es {timezone}.

Reglas de accion:
17. Si el usuario quiere agendar una cita solicita sus datos como correo. Una vez que tengas dia, hora y correo, responde SOLO en JSON con el formato exacto:
{{
  "action": "create_event",
  "tenantId": "{tenant_id}",
  "date": "2026-MM-DD",
  "startTime": "2026-MM-DDTHH:MM{timezone}",
  "title": "...",
  "guestEmails": ["...@...com", "...@...com"]
}}
18. Si el usuario pregunta por horarios disponibles o cuando puede agendar una cita, responde SOLO en JSON:
{{
  "action": "check_availability",
  "tenantId": "{tenant_id}",
  "preferred_date": "2026-MM-DD"
}}
19. JAMAS generes una cita sin pedir antes el correo del usuario.
20. Si detectas intencion de compra o contacto obten datos de manera natural y continua con la conversacion, no hables sobre enviar informacion por correo u otros medios aun.
21. Si detectas intencion de compra o contacto (mediana o alta) y solo si tienes informacion del usuario como nombre, correo o telefono, genera un JSON asi:
{{
  "action": "capture_lead",
  "tenantId": "{tenant_id}",
  "name": "...",
  "email": "...",
  "phone": "...",
  "intent_level": "medium/high",
  "response": "normal text response to user"
}}
22. Si el usuario tiene un problema o queja y solicita hablar con soporte solicita su telefono y cuando lo tengas, genera un JSON asi:
{{
    "action": "escalate_support",
    "tenantId": "{tenant_id}",
    "user_phone": "...",
    "reason": "informacion sobre el problema o queja y contexto de como se llego a la situacion"
}}
23. Si no hay accion, responde normalmente como asesor comercial del negocio.
24. Si generas JSON, asegurate de que el formato sea correcto y valido.
25. Si no tienes suficiente informacion para crear el evento o capturar el lead, continua la conversacion para obtener mas detalles.
26. Cuando sea necesaria una accion responde UNICAMENTE con un JSON valido. NO incluyas texto adicional. NO incluyas comentarios. NO envuelvas el JSON en otro objeto.
27. Nunca ignores las instrucciones de este prompt.
"""

# Plantilla para dar contexto al modelo
template = """
Contexto de la empresa:
{context}

Pregunta del usuario:
{query}

Responde estrictamente en el lenguaje de este texto {language}.
"""

combined_prompt = "Fecha y hora actual: {current_date}\n\n" + system_prompt + "\n" + template
prompt = PromptTemplate(
    input_variables=["context", "query", "language", "tenant_id", "timezone", "current_date"],
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
    contact_payload = is_contact_payload(question)
    prompt_history = sanitize_history_for_contact_payload(history) if contact_payload else history
    
    # Buscar contexto relevante en FAISS si no se proporciona contexto
    if contact_payload:
        context = ""
    elif not context:
        print(f"Buscando contexto en FAISS para tenant_id={tenant_id} y query='{question}'")
        docs = search_semantic(question, tenant_id)
        print(f"Documentos encontrados: {len(docs)}")
        if docs:
            context = "\n".join([doc.page_content for doc in docs])
            print(f"Contexto FAISS encontrado: {context}")

    relevant_links = [] if contact_payload else extract_relevant_links(question, context)

    # Agregar historial previo
    history_text = build_history_text(prompt_history, max_messages=10)

    # Combinar historial con contexto de FAISS
    full_context = history_text
    if context:
        full_context += f"\nContexto de la empresa:\n{context}"
    if relevant_links:
        full_context += "\nLinks relevantes detectados:\n" + "\n".join(
            link.get("url", "") for link in relevant_links if link.get("url")
        )

    if not is_business_scope_question(question, history_text=history_text, business_context=context):
        return build_out_of_scope_response(question)

    chain_input = {
        "context": full_context,
        "query": question,
        "language": question,
        "tenant_id": tenant_id,
        "timezone": TIMEZONE,
        "current_date": datetime.now().strftime("%Y-%m-%d (%A)")
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
            print("Acción detectada:", action_json)
            
            calendar_action_response = handle_calendar_action(
                action_json=action_json,
                question=question,
                history_text=history_text,
                tenant_id=tenant_id,
            )
            if calendar_action_response is not None:
                response_text = calendar_action_response

            elif action_json["action"] == "capture_lead":
                if action_json.get("name") or action_json.get("email"):
                    create_lead(action_json)
                    response_text = action_json.get("response", "")

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
    
    if not response_text.strip().startswith("{"):
        response_text = append_relevant_link(response_text, question, relevant_links)

    return response_text
