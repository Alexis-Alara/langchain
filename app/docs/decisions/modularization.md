# Decision: Modularizacion por Integracion

## Motivo

El proyecto mezclaba en pocos archivos:

- rutas HTTP
- logica de negocio
- clientes de proveedores
- prompts

Eso dificultaba mantener WhatsApp, Meta, voz y web como piezas instalables o modificables por separado.

## Decision

Se reordeno el codigo en:

- `app/modules/<integracion>/prompts`
- `app/modules/<integracion>/routes`
- `app/modules/<integracion>/tools`
- `app/shared/*` para piezas reutilizables reales
- `app/app/*` para bootstrap y composicion

## Alcance

Solo se modularizo lo que ya existia en el repo:

- webchat
- whatsapp
- meta messaging
- twilio voice
- shared: FAISS, Mongo, calendario, leads, historial, token tracking

No se agregaron integraciones nuevas que no estuvieran implementadas.
