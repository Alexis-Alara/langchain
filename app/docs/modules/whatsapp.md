# Modulo WhatsApp

## Proposito

Gestiona el webhook de WhatsApp Business API y el envio de respuestas salientes.

## Estructura

- `routes/router.py`: verificacion y recepcion del webhook.
- `tools/service.py`: cliente de WhatsApp Business API.
- `tools/handler.py`: orquestacion de texto y audio.

## Variables

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_VERIFY_TOKEN`
- `OPENAI_API_KEY`
- `TENANT_ID`
