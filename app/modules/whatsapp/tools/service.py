import logging
from typing import Any, Dict, Optional

import aiohttp
from fastapi import HTTPException

from app.shared.config.settings import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_GRAPH_VERSION,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_VERIFY_TOKEN,
)

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        self.access_token = WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        self.verify_token = WHATSAPP_VERIFY_TOKEN
        self.base_url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{self.phone_number_id}"

    def validate_config(self) -> bool:
        if not self.access_token or not self.phone_number_id:
            logger.error("WhatsApp configuration is incomplete")
            return False
        return True

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        if not self.validate_config():
            raise HTTPException(status_code=500, detail="Configuracion de WhatsApp incompleta")

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=self.get_headers(),
                ) as response:
                    result = await response.json()
                    if response.status == 200:
                        logger.info("WhatsApp message sent to %s", to)
                        return result
                    logger.error("WhatsApp send error: %s - %s", response.status, result)
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Error de WhatsApp API: {result.get('error', {}).get('message', 'Unknown error')}",
                    )
        except aiohttp.ClientError as exc:
            logger.error("WhatsApp connection error: %s", str(exc))
            raise HTTPException(status_code=500, detail="Error de conexion con WhatsApp API")
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Unexpected WhatsApp send error: %s", str(exc))
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "es",
        components: Optional[list] = None,
    ) -> Dict[str, Any]:
        if not self.validate_config():
            raise HTTPException(status_code=500, detail="Configuracion de WhatsApp incompleta")

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/messages",
                    json=payload,
                    headers=self.get_headers(),
                ) as response:
                    result = await response.json()
                    if response.status == 200:
                        logger.info("WhatsApp template sent to %s", to)
                        return result
                    logger.error("WhatsApp template error: %s - %s", response.status, result)
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Error de WhatsApp API: {result.get('error', {}).get('message', 'Unknown error')}",
                    )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Unexpected WhatsApp template error: %s", str(exc))
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    async def download_media(self, media_id: str) -> bytes:
        if not self.validate_config():
            raise HTTPException(status_code=500, detail="Configuracion de WhatsApp incompleta")

        media_info_url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{media_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(media_info_url, headers=self.get_headers()) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=response.status, detail="Error obteniendo URL del media")
                    media_info = await response.json()
                    media_url = media_info.get("url")

                if not media_url:
                    raise HTTPException(status_code=500, detail="URL del media no encontrada")

                async with session.get(
                    media_url,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                ) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=response.status, detail="Error descargando el media")
                    return await response.read()
        except aiohttp.ClientError as exc:
            logger.error("WhatsApp media download error: %s", str(exc))
            raise HTTPException(status_code=500, detail="Error de conexion descargando media")

    def format_phone_number(self, phone: str) -> str:
        formatted = "".join(char for char in phone if char.isdigit() or char == "+")
        if not formatted.startswith("+"):
            if len(formatted) == 10:
                formatted = f"+52{formatted}"
            else:
                formatted = f"+{formatted}"
        return formatted

    def extract_phone_from_whatsapp_id(self, wa_id: str) -> str:
        return wa_id if wa_id.startswith("+") else f"+{wa_id}"


whatsapp_service = WhatsAppService()
