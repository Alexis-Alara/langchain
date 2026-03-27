from app.shared.tools.assistant import generate_answer
from app.shared.tools.chat_history import get_conversation_history, save_message
from app.shared.tools.retrieval import search_semantic
from app.shared.utils.documents import join_page_contents


def process_text_message(message_text: str, tenant_id: str, conversation_id: str, source: str):
    history = get_conversation_history(tenant_id, conversation_id)
    save_message(tenant_id, conversation_id, "user", message_text)

    documents = search_semantic(message_text, tenant_id)
    context = join_page_contents(documents)

    answer = generate_answer(
        message_text,
        history=history,
        context=context,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        source=source,
    )

    save_message(tenant_id, conversation_id, "assistant", answer)
    return answer
