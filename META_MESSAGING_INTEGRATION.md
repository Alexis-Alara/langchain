# Integracion con Messenger e Instagram (Meta Messaging)

Este documento explica como configurar la integracion de Messenger e Instagram en este proyecto.

## Variables de entorno

Agrega estas variables al archivo `.env`:

```env
# Meta Messaging
META_PAGE_ID=tu_meta_page_id
META_PAGE_ACCESS_TOKEN=tu_page_access_token
META_VERIFY_TOKEN=IMPULSO_META_VERIFY_TOKEN
META_APP_SECRET=tu_meta_app_secret
META_GRAPH_VERSION=v21.0
```

## Endpoints implementados

### Webhook de verificacion (GET)

- `GET /api/meta/webhook`
- `GET /api/messenger/webhook`
- `GET /api/instagram/webhook`

Todos validan `hub.verify_token` contra `META_VERIFY_TOKEN`.

### Webhook de mensajes (POST)

- `POST /api/meta/webhook`
- `POST /api/messenger/webhook`
- `POST /api/instagram/webhook`

Procesan eventos entrantes de Messenger/Instagram y responden automaticamente usando el chatbot.

Si defines `META_APP_SECRET`, se valida `X-Hub-Signature-256`.

### Envio manual de mensajes (POST)

- `POST /api/meta/send` (elige plataforma por body)
- `POST /api/messenger/send`
- `POST /api/instagram/send`

## Formato de envio manual

### `/api/meta/send`

```json
{
  "platform": "messenger",
  "to": "1234567890",
  "type": "text",
  "text": {
    "body": "Hola desde Meta Messaging"
  }
}
```

### `/api/messenger/send` y `/api/instagram/send`

```json
{
  "to": "1234567890",
  "type": "text",
  "text": {
    "body": "Hola"
  }
}
```

## Notas de funcionamiento

- Se usa el mismo flujo que WhatsApp: historial + busqueda semantica + `generate_answer`.
- El `conversation_id` queda como:
  - `messenger_{sender_id}`
  - `instagram_{sender_id}`
- El webhook ignora eventos sin texto o mensajes `is_echo`.
