# Mejoras sugeridas para backend de citas

Fecha: 2026-03-19
Referencia principal: [API_ENDPOINTS.md](C:/Users/carme/Desktop/langchain/docs/API_ENDPOINTS.md)

## Endpoints que hoy sí conviene usar para chat

Para un agente conversacional, el flujo más útil queda así:

1. `GET /api/calendar/availability/date`
   Usarlo cuando el usuario pide una fecha concreta como `hoy`, `mañana` o `el viernes`.

2. `GET /api/calendar/availability/suggestions`
   Usarlo cuando el usuario pregunta algo más abierto como `¿cuándo tienes espacio?`.

3. `GET /api/calendar/availability/check`
   Usarlo justo antes de crear la cita para validar el slot exacto.

4. `POST /api/calendar/appointments`
   Usarlo solo cuando ya hay fecha, hora y correo confirmados.

## Lo que hoy ya ayuda

- `GET /api/calendar/availability/date` ya devuelve `totalSlots`.
  Eso permite que el agente responda bien cuando el usuario pregunta si solo existen esos 3 horarios o si hay más.

- `GET /api/calendar/availability/check` evita tener que recalcular disponibilidad manualmente.

- `GET /api/calendar/availability/suggestions` ya resuelve el caso de disponibilidad general a varios días.

## Problemas actuales que conviene corregir en backend

### 1. `POST /api/calendar/appointments` devuelve conflictos en un formato difícil de consumir

Hoy el documento dice que, si el slot no está disponible, el endpoint responde `400` y mete las sugerencias serializadas dentro de `error`.

Eso obliga al cliente a parsear strings para extraer información estructurada.

Recomendación:

```json
{
  "success": false,
  "code": "slot_unavailable",
  "message": "El horario solicitado ya no está disponible.",
  "data": {
    "requestedStartTime": "2026-03-20T09:00:00-06:00",
    "suggestions": [
      {
        "date": "2026-03-20",
        "dayOfWeek": "Viernes",
        "startTime": "10:00",
        "endTime": "11:00",
        "startDateTime": "2026-03-20T10:00:00-06:00",
        "endDateTime": "2026-03-20T11:00:00-06:00",
        "duration": 60
      }
    ]
  }
}
```

### 2. Falta un `code` de error consistente

Para chat y automatización no basta con `message`.
Conviene devolver un `code` machine-readable en estos casos:

- `slot_unavailable`
- `daily_limit_reached`
- `tenant_not_configured`
- `invalid_request`
- `google_sync_failed`

Eso evita heurísticas frágiles en el agente.

### 3. La regla `one appointment per IP per day` es demasiado agresiva

Esto puede romper:

- usuarios detrás de la misma red
- oficinas compartidas
- pruebas locales
- conversaciones de varios leads desde el mismo origen

Mejor opción:

- limitar por `phone`, `email`, `conversationId` o `leadId`
- o dejar la regla por IP solo como rate limit, no como regla de negocio

### 4. Los endpoints `messenger/availability/*` están mejor pensados para AI, pero no están disponibles para este flujo

Esos endpoints tienen una forma más simple para chat, pero requieren `Authorization: Bearer ACCESS_TOKEN`.
Para integraciones conversacionales server-to-server convendría una de estas dos opciones:

- exponer una variante pública controlada por `tenant_id`
- o documentar claramente cómo obtener y refrescar el token para el agente

### 5. Falta consistencia entre shapes de disponibilidad

Hoy existen varias formas:

- `/api/calendar/availability/date`
- `/api/calendar/availability/suggestions`
- `/api/messenger/availability/date/:date`
- `/api/messenger/availability/suggestions`

Sería mejor un contrato más uniforme en campos clave:

- `date`
- `dayOfWeek`
- `startTime`
- `endTime`
- `startDateTime`
- `endDateTime`
- `duration`
- `totalSlots`
- `hasMoreSlots`

### 6. Falta indicar claramente cuántos slots se regresaron vs cuántos existen

Esto es importante para respuestas como:

- `te comparto 3 opciones`
- `no son las únicas, hay 15 disponibles`

Recomendación en respuestas de sugerencias:

```json
{
  "success": true,
  "data": {
    "suggestedSlots": [],
    "returnedSlots": 3,
    "totalSlotsAvailable": 15
  }
}
```

## Cambio recomendado de prioridad

Si el equipo solo va a hacer dos mejoras de backend, las más rentables para el agente son:

1. Hacer estructurado el error de `POST /api/calendar/appointments`
2. Estandarizar un shape simple de disponibilidad para chat con `totalSlotsAvailable`

## Resultado esperado si se corrige esto

Con esos ajustes, el agente puede:

- sonar más humano sin inventar horarios
- responder si hay más opciones además de las mostradas
- manejar objeciones de agenda con menos lógica manual
- agendar con menos reintentos y menos hacks de parsing
