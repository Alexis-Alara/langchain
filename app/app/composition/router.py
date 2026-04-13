from fastapi import FastAPI

from app.app.registry.modules import REGISTERED_MODULES
from app.shared.routes.system import router as system_router


def register_routers(app: FastAPI):
    app.include_router(system_router)
    for module in REGISTERED_MODULES:
        app.include_router(module.load_router(), prefix="/api")
