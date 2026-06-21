from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from app.app.composition.router import register_routers
from app.shared.config.logging import configure_logging
from app.shared.config.settings import APP_DESCRIPTION, APP_NAME, APP_VERSION, CORS_EFFECTIVE_ORIGINS
from app.shared.middleware.rate_limit import limiter
from app.shared.tools.embeddings import init_faiss


def create_app():
    configure_logging()
    init_faiss()

    application = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
    )
    allow_all_origins = "*" in CORS_EFFECTIVE_ORIGINS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all_origins else CORS_EFFECTIVE_ORIGINS,
        allow_credentials=not allow_all_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.state.limiter = limiter
    application.add_exception_handler(429, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)
    register_routers(application)
    return application


app = create_app()
