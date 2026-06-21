import secrets
from typing import Optional

from fastapi import HTTPException, Request

from app.shared.config.settings import MESSAGING_API_TOKEN


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        return ""

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def require_messaging_token(request: Request):
    if not MESSAGING_API_TOKEN:
        raise HTTPException(status_code=503, detail="MESSAGING_API_TOKEN no configurado")

    bearer_token = _extract_bearer_token(request.headers.get("authorization"))
    header_token = request.headers.get("x-messaging-token", "").strip()
    provided_token = bearer_token or header_token

    if not provided_token or not secrets.compare_digest(provided_token, MESSAGING_API_TOKEN):
        raise HTTPException(status_code=401, detail="Token invalido")
