from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_dashboard_service
from app.domain.dashboard import ApplicationSummary, DashboardSummary
from app.services.dashboard import DashboardService

router = APIRouter()

DashboardServiceDependency = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/applications", response_model=list[ApplicationSummary])
def list_applications(dashboard_service: DashboardServiceDependency) -> list[ApplicationSummary]:
    """List every stepper session (Job Description root), newest first."""
    return dashboard_service.list_applications()


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(dashboard_service: DashboardServiceDependency) -> DashboardSummary:
    """Dashboard summary: master resume, counts, and recent applications."""
    return dashboard_service.summary()