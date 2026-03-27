# Variables de Entorno

La plantilla base esta en `.env.example`.

## Requeridas

- `OPENAI_API_KEY`
- `MONGO_URI` o `MONGODB_URI`
- `MONGO_DB` o `MONGODB_DATABASE`

## Por modulo

- WhatsApp: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`
- Meta: `META_PAGE_ACCESS_TOKEN`, `META_VERIFY_TOKEN`
- Voz: `OPENAI_REALTIME_URL`, `TWILIO_MEDIA_STREAM_URL`

## Compatibilidad

El proyecto acepta tanto variables `MONGO_*` como las variantes historicas `MONGODB_*`.
