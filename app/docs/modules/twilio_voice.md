# Modulo Twilio Voice

## Proposito

Atiende llamadas de voz usando Twilio Media Streams y OpenAI Realtime.

## Componentes

- `routes/router.py`: webhook de Twilio y WebSocket de streaming.
- `prompts/voice.py`: instrucciones especificas para voz.
- `tools/handler.py`: herramientas realtime, silencio, historial y callbacks.

## Variables

- `OPENAI_REALTIME_URL`
- `TWILIO_MEDIA_STREAM_URL`
- `SUPPORT_PHONE`
- `TENANT_ID`
