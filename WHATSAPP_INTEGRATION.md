# Integración con WhatsApp Business API

Este documento explica cómo configurar y usar la integración de WhatsApp Business API con el chatbot de Impulso IA.

## Configuración

### 1. Configurar WhatsApp Business API

1. Crear una cuenta de Facebook Business
2. Configurar WhatsApp Business API
3. Obtener los siguientes valores:
   - `WHATSAPP_ACCESS_TOKEN`: Token de acceso de larga duración
   - `WHATSAPP_PHONE_NUMBER_ID`: ID del número de teléfono de WhatsApp Business
   - `WHATSAPP_VERIFY_TOKEN`: Token personalizado para verificación del webhook

### 2. Variables de Entorno

Agregar estas variables al archivo `.env`:

```env
# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=tu_whatsapp_access_token_aqui
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id_aqui
WHATSAPP_VERIFY_TOKEN=IMPULSO_VERIFY_TOKEN
```

### 3. Configurar Webhook

1. **Para desarrollo local con ngrok:**
   ```bash
   # Instalar ngrok
   npm install -g ngrok
   
   # Exponer el servidor local
   ngrok http 8000
   ```

2. **Configurar el webhook en Facebook:**
   - URL del webhook: `https://tu-ngrok-url.ngrok.io/api/whatsapp/webhook`
   - Token de verificación: `IMPULSO_VERIFY_TOKEN`
   - Campos de suscripción: `messages`

## Endpoints Disponibles

### 1. Webhook de Verificación (GET)
```
GET /api/whatsapp/webhook
```
Usado por Facebook para verificar el webhook. Se configura automáticamente.

### 2. Webhook de Mensajes (POST)
```
POST /api/whatsapp/webhook
```
Recibe mensajes de WhatsApp y responde automáticamente usando el chatbot.

**Headers requeridos:**
- `tenant_id`: ID del tenant (opcional, default: "default")

### 3. Enviar Mensaje Manual (POST)
```
POST /api/whatsapp/send
```

**Body:**
```json
{
  "messaging_product": "whatsapp",
  "to": "+5215551234567",
  "type": "text",
  "text": {
    "body": "Hola, este es un mensaje de prueba"
  }
}
```

**Headers requeridos:**
- `tenant_id`: ID del tenant

### 4. Enviar Plantilla (POST)
```
POST /api/whatsapp/send-template
```

**Query Parameters:**
- `to`: Número de teléfono del destinatario
- `template_name`: Nombre de la plantilla aprobada
- `language_code`: Código de idioma (default: "es")

## Funcionalidades

### Manejo de Conversaciones
- Cada número de WhatsApp tiene su propio historial de conversación
- El ID de conversación se genera como: `whatsapp_{numero_telefono}`
- Se mantiene el historial para contexto en futuras respuestas

### Formateo de Números
- Los números se formatean automáticamente para incluir código de país
- Si no se especifica código de país, se asume México (+52)

### Rate Limiting
- Webhook: 20 requests por minuto
- Envío manual: 10 requests por minuto
- Plantillas: 5 requests por minuto

### Logging
- Todos los mensajes enviados y recibidos se registran en los logs
- Los errores se loguean con detalles para debugging

## Ejemplo de Uso

### 1. Recibir y Responder Mensajes Automáticamente

Cuando un usuario envía un mensaje a tu número de WhatsApp Business:
1. WhatsApp envía el mensaje al webhook
2. El sistema busca contexto relevante
3. Genera una respuesta usando GPT
4. Envía la respuesta de vuelta al usuario
5. Guarda ambos mensajes en el historial

### 2. Enviar Mensaje Manual

```python
import requests

response = requests.post(
    "http://localhost:8000/api/whatsapp/send",
    headers={"tenant_id": "mi_empresa"},
    json={
        "messaging_product": "whatsapp",
        "to": "+5215551234567",
        "type": "text",
        "text": {
            "body": "¡Hola! ¿En qué puedo ayudarte?"
        }
    }
)
```

## Solución de Problemas

### Error: "Configuración de WhatsApp incompleta"
- Verificar que `WHATSAPP_ACCESS_TOKEN` y `WHATSAPP_PHONE_NUMBER_ID` estén configurados en `.env`

### Error: "Token de verificación inválido"
- Verificar que `WHATSAPP_VERIFY_TOKEN` coincida con el configurado en Facebook

### Los mensajes no se reciben
- Verificar que el webhook esté configurado correctamente en Facebook
- Revisar que la URL esté accessible públicamente (usar ngrok para desarrollo)
- Verificar los logs del servidor para errores

### Los mensajes no se envían
- Verificar que el número de teléfono esté verificado en WhatsApp Business
- Revisar que el token de acceso tenga los permisos necesarios
- Verificar que el número de destino esté en formato internacional

## Desarrollo

Para probar localmente:

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Configurar variables de entorno en `.env`

3. Iniciar el servidor:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

4. Exponer con ngrok:
   ```bash
   ngrok http 8000
   ```

5. Configurar webhook en Facebook con la URL de ngrok

## Seguridad

- Los webhooks de Facebook incluyen verificación de firma (implementar si es necesario)
- Rate limiting implementado para prevenir abuso
- Logs detallados para auditoría
- Validación de formato de números de teléfono