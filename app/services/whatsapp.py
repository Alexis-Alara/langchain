"""
Servicio especializado para manejar la integración con WhatsApp Business API
"""
import os
import logging
import aiohttp
from typing import Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "IMPULSO_VERIFY_TOKEN")
        self.base_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}"
        
    def validate_config(self) -> bool:
        """Valida que la configuración de WhatsApp esté completa"""
        if not self.access_token or not self.phone_number_id:
            logger.error("Configuración de WhatsApp incompleta")
            return False
        return True
    
    def get_headers(self) -> Dict[str, str]:
        """Obtiene los headers necesarios para las requests a WhatsApp API"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Envía un mensaje de texto a través de WhatsApp Business API
        
        Args:
            to (str): Número de teléfono del destinatario
            message (str): Texto del mensaje
            
        Returns:
            Dict[str, Any]: Respuesta de la API de WhatsApp
        """
        if not self.validate_config():
            raise HTTPException(status_code=500, detail="Configuración de WhatsApp incompleta")
        
        url = f"{self.base_url}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.get_headers()) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Mensaje enviado exitosamente a {to}")
                        return result
                    else:
                        logger.error(f"Error enviando mensaje: {response.status} - {result}")
                        raise HTTPException(
                            status_code=response.status, 
                            detail=f"Error de WhatsApp API: {result.get('error', {}).get('message', 'Unknown error')}"
                        )
        except aiohttp.ClientError as e:
            logger.error(f"Error de conexión con WhatsApp API: {str(e)}")
            raise HTTPException(status_code=500, detail="Error de conexión con WhatsApp API")
        except Exception as e:
            logger.error(f"Error inesperado enviando mensaje: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    async def send_template_message(self, to: str, template_name: str, language_code: str = "es", 
                                  components: Optional[list] = None) -> Dict[str, Any]:
        """
        Envía un mensaje de plantilla a través de WhatsApp Business API
        
        Args:
            to (str): Número de teléfono del destinatario
            template_name (str): Nombre de la plantilla
            language_code (str): Código de idioma (default: es)
            components (list, optional): Componentes de la plantilla
            
        Returns:
            Dict[str, Any]: Respuesta de la API de WhatsApp
        """
        if not self.validate_config():
            raise HTTPException(status_code=500, detail="Configuración de WhatsApp incompleta")
        
        url = f"{self.base_url}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.get_headers()) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Plantilla enviada exitosamente a {to}")
                        return result
                    else:
                        logger.error(f"Error enviando plantilla: {response.status} - {result}")
                        raise HTTPException(
                            status_code=response.status, 
                            detail=f"Error de WhatsApp API: {result.get('error', {}).get('message', 'Unknown error')}"
                        )
        except Exception as e:
            logger.error(f"Error enviando plantilla: {str(e)}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    def format_phone_number(self, phone: str) -> str:
        """
        Formatea un número de teléfono para WhatsApp
        Remueve espacios, guiones y otros caracteres
        """
        # Remover caracteres no numéricos excepto el +
        formatted = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Si no tiene código de país, asumir México (+52)
        if not formatted.startswith('+'):
            if len(formatted) == 10:  # Número mexicano sin código de país
                formatted = f"+52{formatted}"
            else:
                formatted = f"+{formatted}"
        
        return formatted
    
    def extract_phone_from_whatsapp_id(self, wa_id: str) -> str:
        """
        Extrae el número de teléfono del ID de WhatsApp
        """
        # WhatsApp ID generalmente es el número de teléfono con código de país
        return wa_id if wa_id.startswith('+') else f"+{wa_id}"

# Instancia global del servicio
whatsapp_service = WhatsAppService()