from pydantic import BaseModel

class QueryRequest(BaseModel):
    tenant_id: str
    question: str

class QueryResponse(BaseModel):
    answers: list
