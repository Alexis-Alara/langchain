# langchain

Backend FastAPI reorganizado con arquitectura modular por integracion.

## Estructura

- `app/modules/webchat`: endpoint conversacional web.
- `app/modules/whatsapp`: webhook y cliente de WhatsApp Business API.
- `app/modules/meta`: webhook y cliente para Messenger e Instagram.
- `app/modules/twilio_voice`: entrada de voz con Twilio Media Streams y OpenAI Realtime.
- `app/shared`: piezas reutilizables como prompts, configuracion, almacenamiento, calendario, FAISS, historial y tracking.
- `app/app`: bootstrap, composicion y registro de modulos.
- `app/docs`: documentacion de arquitectura, setup y decisiones.

## Arranque

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Configurar modulos

Para generar una configuracion base solo con los modulos que necesitas:

```bash
python -m app.scripts.configure_modules --modules whatsapp --output .env
```

Ejemplo con varios modulos:

```bash
python -m app.scripts.configure_modules --modules whatsapp,webchat --output .env
```

Ver modulos disponibles:

```bash
python -m app.scripts.configure_modules --list
```

Generar, validar y arrancar en un solo paso:

```bash
python -m app.scripts.configure_modules --modules whatsapp --output .env --run --reload
```

Si faltan variables obligatorias, el script te las lista y no arranca la app.

## Documentacion

- [Arquitectura](app/docs/architecture/overview.md)
- [Setup](app/docs/setup/environment.md)
- [Decision de modularizacion](app/docs/decisions/modularization.md)
