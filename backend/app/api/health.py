from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import settings
from app.schemas import DatabaseStatus, HealthDatabase, HealthResponse
from app.services.health import HealthService, get_health_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    database_ok = service.database_ok()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        database=HealthDatabase(
            status=DatabaseStatus.ok if database_ok else DatabaseStatus.unavailable
        ),
    )