# app/main.py
# Archivo principal para iniciar la aplicación FastAPI
# Uso:  python3 -m uvicorn app.main:app --reload
from fastapi import FastAPI
from app.embeddings import init_faiss
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from app.api.routes import router as api_router
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Inicializar FAISS al iniciar la app
init_faiss()

# Configurar limitador de tasa
limiter = Limiter(key_func=lambda request: request.headers.get("x-api-key", "anonymous"))

app = FastAPI(
    title="Impulso Chatbot API",
    description="API para chatbot con integración de WhatsApp Business",
    version="1.0.0"
)

# Middleware de slowapi
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Montar las rutas de la API
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Impulso Chatbot API",
        "endpoints": [
            "/api/query - Chat endpoint",
            "/api/whatsapp/webhook - WhatsApp webhook",
            "/api/whatsapp/send - Send WhatsApp message",
            "/api/whatsapp/send-template - Send WhatsApp template"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
