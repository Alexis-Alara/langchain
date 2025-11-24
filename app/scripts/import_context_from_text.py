# Script para importar contextos desde un archivo JSON y agregarlos a Mongo y FAISS
# Uso: python3 -m app.scripts.import_context_from_text
import json
from app.embeddings import add_document

# Ruta del archivo JSON
JSON_PATH = "app/scripts/impulso_context.json"

# Cargar contextos desde el archivo
with open(JSON_PATH, "r", encoding="utf-8") as f:
    contextos = json.load(f)

# Agregar cada contexto a Mongo y FAISS
for ctx in contextos:
    add_document(ctx["text"], ctx["tenantId"])
    print(f"Documento agregado para tenant_id={ctx['tenantId']}")