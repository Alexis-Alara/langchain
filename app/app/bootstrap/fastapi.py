from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from app.app.composition.router import register_routers
from app.shared.config.logging import configure_logging
from app.shared.config.settings import APP_DESCRIPTION, APP_NAME, APP_VERSION
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
    application.state.limiter = limiter
    application.add_exception_handler(429, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)
    register_routers(application)
    return application


app = create_app()
