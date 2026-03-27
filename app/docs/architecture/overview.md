# Arquitectura Modular

El directorio `app/` funciona como el `src/` del proyecto.

## Modulos de integracion

- `app/modules/webchat`
- `app/modules/whatsapp`
- `app/modules/meta`
- `app/modules/twilio_voice`

Cada modulo contiene:

- `prompts`: instrucciones y notas del canal.
- `routes`: entrypoints HTTP o WebSocket.
- `tools`: adaptadores, handlers y logica propia del canal.

## Compartido

`app/shared` concentra lo reutilizable entre modulos:

- `config`: settings, base de datos y logging.
- `prompts`: prompt compartido del asistente.
- `tools`: FAISS, retrieval, historial, calendario, tracking y utilidades de IA.
- `routes`: endpoints globales como `/` y `/health`.
- `middleware`, `types`, `constants`, `utils`: soporte transversal.

## Composicion

- `app/app/registry/modules.py`: inventario de modulos activos.
- `app/app/composition/router.py`: ensambla routers.
- `app/app/bootstrap/fastapi.py`: crea la aplicacion FastAPI.

`app/main.py` queda como entrypoint minimo.
