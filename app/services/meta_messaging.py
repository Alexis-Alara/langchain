"""
Servicio para manejar integracion con Messenger e Instagram Messaging (Meta Graph API).
"""
import os
import hmac
import hashlib
import logging
from typing import Dict, Any

import aiohttp
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class MetaMessagingService:
    def __init__(self):
        self.page_id = os.getenv("META_PAGE_ID")
        self.page_access_token = os.getenv("META_PAGE_ACCESS_TOKEN")
        self.verify_token = os.getenv("META_VERIFY_TOKEN", "IMPULSO_META_VERIFY_TOKEN")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.graph_version = os.getenv("META_GRAPH_VERSION", "v21.0")
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"

    def validate_config(self) -> bool:
        """Valida configuracion minima para enviar mensajes."""
        if not self.page_id or not self.page_access_token:
            logger.error("Configuracion de Meta Messaging incompleta")
            return False
        return True

    def get_headers(self) -> Dict[str, str]:
        """Headers para requests al Graph API."""
        return {
            "Authorization": f"Bearer {self.page_access_token}",
            "Content-Type": "application/json",
        }

    def normalize_platform(self, platform: str) -> str:
        """Normaliza nombres de plataforma permitidos."""
        normalized = (platform or "").strip().lower()
        if normalized in ("facebook", "messenger", "page"):
            return "messenger"
        if normalized in ("instagram", "ig"):
            return "instagram"
        raise HTTPException(status_code=400, detail="Plataforma invalida. Usa 'messenger' o 'instagram'")

    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """
        Verifica firma X-Hub-Signature-256 del webhook.
        Si no hay APP_SECRET configurado, no bloquea.
        """
        if not self.app_secret:
            return True

        if not signature_header:
            logger.warning("Falta header X-Hub-Signature-256")
            return False

        try:
            scheme, signature = signature_header.split("=", 1)
        except ValueError:
            return False

        if scheme != "sha256":
            return False

        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def send_text_message(self, platform: str, recipient_id: str, message: str) -> Dict[str, Any]:
        """Envia mensaje de texto a Messenger o Instagram."""
        if not self.validate_config():
            raise HTTPException(status_code=500, detail="Configuracion de Meta Messaging incompleta")

        normalized_platform = self.normalize_platform(platform)
        url = f"{self.base_url}/{self.page_id}/messages"

        payload: Dict[str, Any] = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": message},
        }

        params = {"platform": "instagram"} if normalized_platform == "instagram" else None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    params=params,
                    json=payload,
                    headers=self.get_headers(),
                ) as response:
                    result = await response.json()

                    if response.status in (200, 201):
                        logger.info("Mensaje enviado a %s (%s)", recipient_id, normalized_platform)
                        return result

                    logger.error(
                        "Error enviando mensaje Meta: %s - %s",
                        response.status,
                        result,
                    )
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Error de Meta API: {result.get('error', {}).get('message', 'Unknown error')}",
                    )
        except aiohttp.ClientError as e:
            logger.error("Error de conexion con Meta API: %s", str(e))
            raise HTTPException(status_code=500, detail="Error de conexion con Meta API")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error inesperado enviando mensaje Meta: %s", str(e))
            raise HTTPException(status_code=500, detail="Error interno del servidor")


meta_messaging_service = MetaMessagingService()
