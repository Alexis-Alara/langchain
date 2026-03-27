def join_page_contents(documents):
    return "\n".join(
        document.page_content
        for document in documents or []
        if getattr(document, "page_content", None)
    )
