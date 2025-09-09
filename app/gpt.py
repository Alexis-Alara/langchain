import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.services.retrieval import search_semantic

# Modelo GPT
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",  # puedes usar gpt-3.5-turbo si quieres más barato
    temperature=0.2
)

# Plantilla para dar contexto al modelo
template = """
Eres un asistente virtual de soporte para clientes.

Contexto de la empresa:
{context}

Pregunta del usuario:
{query}

Responde de forma natural, clara y útil.
"""

prompt = PromptTemplate(
    input_variables=["context", "query"],
    template=template
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

    chain_input = {"context": full_context, "query": question}

    print("Generando respuesta con el siguiente input al modelo:")
    print(chain_input)
    # Llamada correcta usando invoke
    response = llm.invoke(prompt.format(**chain_input))

    return response.content