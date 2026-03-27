from app.shared.tools.chat_flow import process_text_message


def handle_query(question: str, tenant_id: str, conversation_id: str):
    return process_text_message(
        question,
        tenant_id,
        conversation_id,
        source="web",
    )
