from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.modules.webchat.tools.handler import handle_query
from app.shared.middleware.rate_limit import limiter

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    tenant_id: str
    conversation_id: str


class QueryResponse(BaseModel):
    answer: str


@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_endpoint(body: QueryRequest, request: Request):
    tenant_id = request.headers.get("tenant_id") or body.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant-id header is required")

    return {
        "answer": handle_query(
            body.question,
            tenant_id,
            body.conversation_id,
        )
    }
