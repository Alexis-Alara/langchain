import logging
import os

from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from .availability import format_availability_suggestions, summarize_availability_data

load_dotenv()

logger = logging.getLogger(__name__)

sales_llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    temperature=0.45,
)

availability_response_prompt = PromptTemplate(
    input_variables=["sales_context", "history", "question", "availability_summary"],
    template="""
Eres un asesor comercial humano que conversa por chat.

Tu tono debe sonar como una persona real: cercano, seguro, claro, natural y con mentalidad de venta consultiva.

Instrucciones:
1. Responde primero la duda exacta del usuario.
2. Si pregunta si solo existen esos horarios, responde de forma directa usando el total real de espacios.
3. Se explicito. Si hay mas horarios aparte de los que vas a mencionar, dilo claramente.
4. No inventes horarios, condiciones ni politicas.
5. No suenes robotico ni uses frases genericas como "te sugiero estos horarios disponibles".
6. Recomienda los horarios con mas sentido y cierra con una pregunta breve para avanzar.
7. Usa el mismo idioma del usuario.
8. No uses JSON.

Contexto comercial:
{sales_context}

Historial reciente:
{history}

Pregunta actual:
{question}

Disponibilidad real:
{availability_summary}
""",
)


def generate_human_availability_response(question, history_text, availability_data, sales_context):
    availability_summary = summarize_availability_data(availability_data)
    if not availability_summary:
        return "En este momento no pude consultar la agenda. Si quieres, lo intento de nuevo en un momento."

    try:
        response = sales_llm.invoke(
            availability_response_prompt.format(
                sales_context=sales_context,
                history=history_text or "Sin historial previo relevante.",
                question=question,
                availability_summary=availability_summary,
            )
        )
        response_text = (response.content or "").strip()
        if response_text:
            return response_text
    except Exception as exc:
        logger.error("Error generando respuesta humana de disponibilidad: %s", str(exc))

    return format_availability_suggestions(availability_data)
