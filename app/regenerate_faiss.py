#!/usr/bin/env python3
"""
Script para regenerar el índice FAISS desde la knowledge base de MongoDB.

Uso:
    python regenerate_faiss.py              # Regenera todo
    python regenerate_faiss.py --tenant ID  # Regenera solo un tenant
    python regenerate_faiss.py --clear      # Limpia el índice antiguo
"""

import os
import shutil
import argparse
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from app.db.mongo import knowledge_collection as collection
from app.db.config import OPENAI_API_KEY, MONGO_DB

FAISS_PATH = "faiss_index"
FAISS_BACKUP = f"faiss_index.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup_faiss():
    """Crea backup del índice actual."""
    if os.path.exists(FAISS_PATH):
        shutil.copytree(FAISS_PATH, FAISS_BACKUP)
        print(f"✅ Backup creado en: {FAISS_BACKUP}")
        return True
    return False

def clear_faiss():
    """Elimina el índice FAISS actual."""
    if os.path.exists(FAISS_PATH):
        shutil.rmtree(FAISS_PATH)
        print(f"🗑️  FAISS eliminado: {FAISS_PATH}")
        return True
    return False

def regenerate_all():
    """Regenera el índice FAISS con toda la knowledge base."""
    print("\n" + "="*60)
    print("🔄 REGENERANDO FAISS INDEX DESDE MONGODB")
    print("="*60)
    
    # Hacer backup
    print("\n📦 Creando backup...")
    backup_faiss()
    
    # Inicializar embeddings
    print("\n🤖 Conectando con OpenAI embeddings...")
    embeddings_model = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    
    # Obtener documentos de Mongo
    print("\n📖 Leyendo knowledge base de MongoDB...")
    docs = list(collection.find({}))
    print(f"   → Encontrados {len(docs)} documentos")
    
    if not docs:
        print("⚠️  No hay documentos en la knowledge base!")
        return False
    
    # Preparar datos para FAISS
    texts = []
    metadatas = []
    
    for i, doc in enumerate(docs):
        text = doc.get("text", "")
        if text:
            texts.append(text)
            metadatas.append({
                "tenantId": doc.get("tenantId", "unknown"),
                "source": doc.get("source", "unknown"),
                "createdAt": str(doc.get("createdAt", "")),
                "_id": str(doc.get("_id", ""))
            })
            
            if (i + 1) % 10 == 0:
                print(f"   → Procesados {i + 1}/{len(docs)} documentos")
    
    print(f"\n✨ Creando índice FAISS con {len(texts)} documentos...")
    
    try:
        # Crear nuevo índice
        vector_store = FAISS.from_texts(texts, embeddings_model, metadatas=metadatas)
        
        # Guardar en disco
        vector_store.save_local(FAISS_PATH)
        print(f"✅ Índice guardado en: {FAISS_PATH}")
        
        # Estadísticas
        index_stats = {
            "total_documents": len(texts),
            "embedding_model": "OpenAI",
            "created_at": datetime.now().isoformat(),
            "db": MONGO_DB
        }
        
        print("\n📊 Estadísticas del nuevo índice:")
        for key, value in index_stats.items():
            print(f"   {key}: {value}")
        
        print("\n✅ FAISS regenerado exitosamente!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la regeneración: {e}")
        print(f"⚠️  Restaurando desde backup: {FAISS_BACKUP}")
        if os.path.exists(FAISS_BACKUP):
            shutil.rmtree(FAISS_PATH)
            shutil.copytree(FAISS_BACKUP, FAISS_PATH)
            print("✅ Backup restaurado")
        return False

def regenerate_by_tenant(tenant_id: str):
    """Regenera el índice FAISS solo para un tenant específico."""
    print("\n" + "="*60)
    print(f"🔄 REGENERANDO FAISS PARA TENANT: {tenant_id}")
    print("="*60)
    
    # Hacer backup
    print("\n📦 Creando backup...")
    backup_faiss()
    
    # Inicializar embeddings
    print("\n🤖 Conectando con OpenAI embeddings...")
    embeddings_model = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    
    # Obtener documentos de Mongo para el tenant
    print(f"\n📖 Leyendo knowledge base de MongoDB para tenant: {tenant_id}...")
    docs = list(collection.find({"tenantId": tenant_id}))
    print(f"   → Encontrados {len(docs)} documentos")
    
    if not docs:
        print(f"⚠️  No hay documentos para el tenant {tenant_id}")
        return False
    
    # Preparar datos
    texts = [doc.get("text", "") for doc in docs if doc.get("text")]
    metadatas = [
        {
            "tenantId": doc.get("tenantId"),
            "source": doc.get("source", "unknown"),
            "_id": str(doc.get("_id", ""))
        }
        for doc in docs if doc.get("text")
    ]
    
    try:
        # Crear índice
        vector_store = FAISS.from_texts(texts, embeddings_model, metadatas=metadatas)
        vector_store.save_local(FAISS_PATH)
        
        print(f"\n✅ FAISS regenerado para {tenant_id} con {len(texts)} documentos")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Regenerar índice FAISS desde MongoDB knowledge base"
    )
    parser.add_argument(
        "--tenant",
        type=str,
        help="Regenerar solo para un tenant específico"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Limpiar el índice antiguo sin backup"
    )
    
    args = parser.parse_args()
    
    if args.clear:
        print("⚠️  Limpiando índice actual...")
        clear_faiss()
    
    if args.tenant:
        success = regenerate_by_tenant(args.tenant)
    else:
        success = regenerate_all()
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
