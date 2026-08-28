from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.resumes import router as resumes_router
from app.config import settings
from app.errors import register_exception_handlers

app = FastAPI(title=settings.app_name)
app.include_router(health_router, prefix="/api")
app.include_router(resumes_router, prefix="/api")
register_exception_handlers(app)