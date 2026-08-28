from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import settings
from app.errors import register_exception_handlers

app = FastAPI(title=settings.app_name)
app.include_router(health_router, prefix="/api")
register_exception_handlers(app)