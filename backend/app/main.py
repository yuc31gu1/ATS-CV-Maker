from fastapi import FastAPI

from app.api import health, job_descriptions, jobs
from app.api.resumes import router as resumes_router
from app.config import settings
from app.errors import register_exception_handlers

app = FastAPI(title=settings.app_name)
app.include_router(health.router, prefix="/api")
app.include_router(resumes_router, prefix="/api")
app.include_router(job_descriptions.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
register_exception_handlers(app)