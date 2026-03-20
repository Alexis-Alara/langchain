# Mejoras sugeridas para Knowledge Base

## Problema detectado

El servicio Python consulta conocimiento con un indice FAISS local en disco (`faiss_index`).
Si la base de conocimiento cambia desde el back o desde el portal, Mongo puede tener la version nueva pero FAISS seguir con una version vieja.

Resultado:
- el dato existe en Mongo
- pero no siempre llega al contexto del agente
- y el agente puede responder bien a medias, sin incluir links o pasos exactos

## Impacto real observado

Caso real:
- En Mongo existe una entrada como:
  - `Se recomienda este link cuando el cliente no sabe que plan necesita https://impulso-ia-21c52.web.app/`
- La pregunta `no se que plan necesito` no siempre recuperaba esa entrada desde FAISS.

## Recomendaciones para back

### 1. Exponer una version de knowledge base

Agregar una forma de saber si la KB cambio:
- `knowledgeBaseVersion`
- `updatedAt` global
- hash del contenido

Esto permitiria que el servicio Python invalide o reconstruya su indice cuando detecte cambios.

### 2. Emitir evento al crear, editar o borrar entradas

Cuando se use:
- `POST /api/portal/knowledge-base`
- `PUT /api/portal/knowledge-base/:id`
- `DELETE /api/portal/knowledge-base/:id`
- `POST /api/portal/knowledge-base/bulk-update`

conviene disparar un evento o webhook interno para que el servicio de chat:
- agregue el documento nuevo al indice
- actualice el documento editado
- elimine el documento borrado

### 3. Exponer un endpoint de busqueda textual simple

Ademas de FAISS, conviene tener una busqueda deterministica tipo:
- `GET /api/portal/knowledge-base/search?query=...`

Idealmente con:
- score
- coincidencias exactas
- urls detectadas
- categoria

Eso ayuda mucho para casos donde el usuario hace preguntas casi literales y espera un link exacto.

### 4. Separar metadata util del texto libre

Para respuestas comerciales es mejor no depender solo de texto plano.
Conviene guardar campos estructurados como:
- `title`
- `category`
- `recommendedUrl`
- `recommendedCta`
- `keywords`
- `priority`

Ejemplo:

```json
{
  "title": "Plan recomendado cuando no sabe cual elegir",
  "category": "ventas",
  "keywords": ["plan", "no se que plan necesito", "onboarding", "formulario"],
  "recommendedUrl": "https://impulso-ia-21c52.web.app/",
  "recommendedCta": "Puedes revisar aqui el formulario para identificar el plan ideal"
}
```

### 5. Permitir marcar entradas como `high_priority`

Hay piezas de conocimiento que deben ganar siempre:
- links de onboarding
- formularios
- pagos
- soporte
- agendado

Un campo como `priority: high` permitiria reordenar resultados antes de enviarlos al agente.

## Resultado esperado

Con estas mejoras:
- el agente encontrara mas seguido el contenido correcto
- incluira links utiles en preguntas comerciales
- dependera menos de coincidencias semanticas inestables
- y tendra menos respuestas "correctas pero incompletas"
