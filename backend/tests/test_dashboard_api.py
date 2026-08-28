"""The dashboard + applications read model (product UX, T8)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_dashboard_service
from app.domain.analysis import JobAnalysis, JobDescription
from app.domain.dashboard import ApplicationSummary, DashboardSummary
from app.domain.generated import GeneratedResume
from app.domain.resume import PersonalInformation, Resume
from app.domain.tailoring import TailoredResume
from app.main import app
from app.repositories.in_memory import InMemoryRepository
from app.repositories.resume import InMemoryResumeRepository
from app.services.dashboard import DashboardService

NOW = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def resume(full_name: str = "Ada Lovelace") -> Resume:
    return Resume(
        id="resume-1",
        personal_information=PersonalInformation(full_name=full_name),
        summary="Deterministic document pipelines.",
    )


def job_description(
    job_description_id: str, *, created_at: datetime = NOW, company: str | None = None
) -> JobDescription:
    return JobDescription(
        id=job_description_id,
        company=company,
        role="Engineer",
        location="Remote",
        jd_text="Role: Engineer\n- Must have Python\n",
        created_at=created_at,
    )


def analysis(job_description_id: str) -> JobAnalysis:
    return JobAnalysis(
        id=job_description_id,
        job_description_id=job_description_id,
        role="Engineer",
        requirements=[],
        created_at=NOW,
    )


def tailored(job_description_id: str) -> TailoredResume:
    return TailoredResume(
        job_description_id=job_description_id,
        resume_version_id="version-1",
        resume_id="resume-1",
        personal_information=PersonalInformation(full_name="Ada Lovelace"),
        summary="Backend engineer.",
        created_at=NOW,
    )


def generated(job_description_id: str) -> GeneratedResume:
    return GeneratedResume(
        job_description_id=job_description_id,
        resume_version_id="version-1",
        resume_id="resume-1",
        latex_key=f"latex/{job_description_id}.tex",
        pdf_key=f"pdf/{job_description_id}.pdf",
        created_at=NOW,
    )


@pytest.fixture
def dashboard_service() -> DashboardService:
    jd_repo = InMemoryRepository()
    jd_repo.add("jd-old", job_description("jd-old", created_at=NOW - timedelta(days=2)))
    jd_repo.add("jd-new", job_description("jd-new", company="Acme", created_at=NOW))
    analysis_repo = InMemoryRepository()
    analysis_repo.add("jd-new", analysis("jd-new"))
    tailored_repo = InMemoryRepository()
    tailored_repo.add("jd-old", tailored("jd-old"))
    generated_repo = InMemoryRepository()
    generated_repo.add("jd-old", generated("jd-old"))
    resume_repo = InMemoryResumeRepository()
    resume_repo.create(resume())

    service = DashboardService(
        resume_repository=resume_repo,
        jd_repository=jd_repo,
        analysis_repository=analysis_repo,
        tailored_repository=tailored_repo,
        generated_repository=generated_repo,
    )
    app.dependency_overrides[get_dashboard_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_dashboard_service, None)


@pytest.fixture
def api_client(dashboard_service: DashboardService) -> TestClient:
    with TestClient(app) as client:
        yield client


def test_list_applications_newest_first_with_stage_flags(api_client: TestClient):
    resp = api_client.get("/api/applications")
    assert resp.status_code == 200
    applications = [ApplicationSummary.model_validate(item) for item in resp.json()]

    assert [app.job_description_id for app in applications] == ["jd-new", "jd-old"]

    newest = applications[0]
    assert newest.company == "Acme"
    assert newest.has_analysis is True
    assert newest.has_tailored is False
    assert newest.has_generated is False

    oldest = applications[1]
    assert oldest.has_analysis is False
    assert oldest.has_tailored is True
    assert oldest.has_generated is True


def test_dashboard_summary_reports_master_and_counts(api_client: TestClient):
    resp = api_client.get("/api/dashboard")
    assert resp.status_code == 200
    summary = DashboardSummary.model_validate(resp.json())

    assert summary.master_resume is not None
    assert summary.master_resume.personal_information.full_name == "Ada Lovelace"
    assert summary.tailored_cv_count == 1
    assert summary.analyzed_jobs_count == 1
    assert [app.job_description_id for app in summary.recent_applications] == [
        "jd-new",
        "jd-old",
    ]


def test_dashboard_without_master_resume_reports_null():
    service = DashboardService(
        resume_repository=InMemoryResumeRepository(),
        jd_repository=InMemoryRepository(),
        analysis_repository=InMemoryRepository(),
        tailored_repository=InMemoryRepository(),
        generated_repository=InMemoryRepository(),
    )
    summary = service.summary()
    assert summary.master_resume is None
    assert summary.tailored_cv_count == 0
    assert summary.analyzed_jobs_count == 0
    assert summary.recent_applications == []