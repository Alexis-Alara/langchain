# Variables de Entorno

La plantilla base esta en `.env.example`.

## Activacion de modulos

La aplicacion lee `ENABLED_MODULES`.

Ejemplos:

- `ENABLED_MODULES=whatsapp`
- `ENABLED_MODULES=whatsapp,webchat`
- `ENABLED_MODULES=all`

Tambien puedes generar el archivo automaticamente:

```bash
python -m app.scripts.configure_modules --modules whatsapp --output .env
```

Y si quieres generar, validar y arrancar:

```bash
python -m app.scripts.configure_modules --modules whatsapp --output .env --run --reload
```

El script valida automaticamente las variables obligatorias para los modulos elegidos.

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
