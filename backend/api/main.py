from fastapi import FastAPI

from api.routes.health import router as health_router
from api.settings import get_settings


def create_application() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.include_router(health_router)
    return application


app = create_application()
