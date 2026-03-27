from app.shared.config.settings import BUSINESS_RESUME, TIMEZONE
from app.shared.prompts.assistant import system_prompt

VOICE_PROMPT_ADDITION = (
    "\n\nINSTRUCCIONES ADICIONALES PARA VOZ:"
    "\n- Estas atendiendo una llamada telefonica. Responde siempre de forma oral, natural y concisa."
    "\n- No uses JSON, listas ni Markdown en tus respuestas habladas."
    "\n- Cuando necesites ejecutar una accion usa las herramientas disponibles."
    "\n- Si no entiendes algo, pide al usuario que lo repita amablemente."
    "\n- Usa un tono profesional, directo y frases cortas."
)


def build_voice_instructions(faiss_context: str, tenant_id: str, timezone: str = TIMEZONE):
    context_chunks = [chunk for chunk in [faiss_context, BUSINESS_RESUME] if chunk]
    context_section = ""
    if context_chunks:
        context_section = "\n\nCONTEXTO DE LA EMPRESA:\n" + "\n".join(context_chunks)

    return (
        system_prompt.replace("{tenant_id}", tenant_id or "").replace("{timezone}", timezone or "UTC")
        + context_section
        + VOICE_PROMPT_ADDITION
    )
