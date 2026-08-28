"""The synchronous GENERATE API: render, compile, validate, analyze, download."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_analysis_service,
    get_generation_service,
    get_job_service,
    get_matching_service,
    get_tailoring_service,
)
from app.errors import PdfValidationFailed
from app.llm.fixture import FixtureLLMProvider
from app.main import app
from app.pdf.validator import PdfValidationReport
from app.repositories.in_memory import InMemoryRepository
from app.repositories.resume import InMemoryResumeRepository
from app.services.analysis import AnalysisService
from app.services.ats import AtsAnalysisService
from app.services.generation import GenerationService
from app.services.jobs import JobService
from app.services.matching import MatchingService
from app.services.resume import ResumeService, get_resume_service
from app.services.tailoring import TailoringService
from app.storage.local import LocalStorageService

SAMPLE_JD = """\
Role: Senior Backend Engineer
Location: Remote

Requirements:
- Experience with FastAPI
"""


def resume_payload() -> dict:
    return {
        "schema_version": 1,
        "personal_information": {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "website": "https://example.com",
        },
        "summary": "Backend engineer who builds API platforms.",
        "skills": {"frameworks": ["FastAPI"]},
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2021-03",
                "bullets": ["Built the ordering API with FastAPI"],
            }
        ],
    }


class FakeCompiler:
    def compile(self, tex: str, work_dir: Path) -> Path:
        pdf = work_dir / "main.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake generated output")
        return pdf


class FakeValidator:
    """Accepts the fake PDF and returns a report over the tailored content."""

    def validate(self, pdf_bytes: bytes, tailored) -> PdfValidationReport:
        skills = " ".join(" ".join(names) for names in tailored.skills.values())
        text = (
            f"{tailored.personal_information.full_name} "
            f"{tailored.personal_information.email} {tailored.summary} {skills}"
        )
        return PdfValidationReport(
            extracted_text=text,
            page_count=1,
            single_column=True,
            standard_headings=True,
            critical_info_in_body=True,
            unexpected_tables=0,
            unexpected_graphics=0,
        )


class FailingValidator(FakeValidator):
    """Rejects every PDF with a structured PDF_VALIDATION_FAILED."""

    def validate(self, pdf_bytes: bytes, tailored) -> PdfValidationReport:
        raise PdfValidationFailed("PDF could not be extracted or measured")


@pytest.fixture
def services(tmp_path) -> dict:
    job_service = JobService(InMemoryRepository())
    analysis_repo = InMemoryRepository()
    match_repo = InMemoryRepository()
    analysis_service = AnalysisService(
        jd_repository=InMemoryRepository(),
        analysis_repository=analysis_repo,
        llm_provider=FixtureLLMProvider(),
    )
    matching_service = MatchingService(
        analysis_repository=analysis_repo,
        match_repository=match_repo,
    )
    resume_service = ResumeService(InMemoryResumeRepository())
    tailored_repo = InMemoryRepository()
    tailoring_service = TailoringService(
        version_repository=InMemoryRepository(),
        tailored_repository=tailored_repo,
        resume_repository=resume_service._repository,
        analysis_repository=analysis_repo,
        match_repository=match_repo,
        llm_provider=FixtureLLMProvider(),
    )
    generation_service = GenerationService(
        tailored_repository=tailored_repo,
        generated_repository=InMemoryRepository(),
        storage=LocalStorageService(tmp_path / "storage"),
        compiler=FakeCompiler(),
        validator=FakeValidator(),
        ats=AtsAnalysisService(
            analysis_repository=analysis_repo,
            match_repository=match_repo,
        ),
    )

    app.dependency_overrides[get_job_service] = lambda: job_service
    app.dependency_overrides[get_analysis_service] = lambda: analysis_service
    app.dependency_overrides[get_matching_service] = lambda: matching_service
    app.dependency_overrides[get_resume_service] = lambda: resume_service
    app.dependency_overrides[get_tailoring_service] = lambda: tailoring_service
    app.dependency_overrides[get_generation_service] = lambda: generation_service
    return {
        "tailoring_service": tailoring_service,
        "generation_service": generation_service,
    }


@pytest.fixture
def api_client(services: dict) -> TestClient:
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def seed_tailored_job(client: TestClient) -> str:
    resume_resp = client.post("/api/resumes", json=resume_payload())
    assert resume_resp.status_code == 201
    resume_id = resume_resp.json()["id"]

    submitted = client.post("/api/job-descriptions", json={"jd_text": SAMPLE_JD})
    assert submitted.status_code == 201
    job_description_id = submitted.json()["job_description_id"]

    match_resp = client.get(
        f"/api/job-descriptions/{job_description_id}/match",
        params={"resume_id": resume_id},
    )
    assert match_resp.status_code == 200

    tailor_resp = client.post(
        f"/api/resumes/{resume_id}/tailor", json={"job_description_id": job_description_id}
    )
    assert tailor_resp.status_code == 201
    job = client.get(f"/api/jobs/{tailor_resp.json()['job_id']}")
    assert job.json()["status"] == "SUCCEEDED"
    return job_description_id


def test_generate_document_end_to_end(api_client: TestClient):
    job_description_id = seed_tailored_job(api_client)

    resp = api_client.post(f"/api/job-descriptions/{job_description_id}/generated")
    assert resp.status_code == 201
    body = resp.json()
    assert body["job_description_id"] == job_description_id
    assert body["resume_version_id"]
    assert body["latex_key"] == f"latex/{job_description_id}.tex"
    assert body["pdf_key"] == f"pdf/{job_description_id}.pdf"

    fetched = api_client.get(f"/api/job-descriptions/{job_description_id}/generated")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_generated_pdf_is_downloadable(api_client: TestClient):
    job_description_id = seed_tailored_job(api_client)
    api_client.post(f"/api/job-descriptions/{job_description_id}/generated")

    pdf = api_client.get(f"/api/job-descriptions/{job_description_id}/generated/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert "attachment; filename=" in pdf.headers["content-disposition"]


def test_generated_latex_is_downloadable(api_client: TestClient):
    job_description_id = seed_tailored_job(api_client)
    api_client.post(f"/api/job-descriptions/{job_description_id}/generated")

    latex = api_client.get(f"/api/job-descriptions/{job_description_id}/generated/latex")
    assert latex.status_code == 200
    assert latex.headers["content-type"] == "application/x-tex"
    assert latex.content.startswith(b"\\documentclass")
    assert "attachment; filename=" in latex.headers["content-disposition"]


def test_generated_resume_pins_to_resume_version(api_client: TestClient):
    job_description_id = seed_tailored_job(api_client)
    tailored = api_client.get(
        f"/api/job-descriptions/{job_description_id}/tailored"
    ).json()

    resp = api_client.post(f"/api/job-descriptions/{job_description_id}/generated")
    assert resp.json()["resume_version_id"] == tailored["resume_version_id"]
    assert resp.json()["resume_id"] == tailored["resume_id"]


def test_generated_missing_before_generation_returns_not_found(api_client: TestClient):
    for path in ("", "/pdf", "/latex"):
        resp = api_client.get(f"/api/job-descriptions/jd-missing/generated{path}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_generate_without_tailored_resume_returns_not_found(api_client: TestClient):
    resp = api_client.post("/api/job-descriptions/jd-missing/generated")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_generate_is_repeatable_and_stable(api_client: TestClient):
    job_description_id = seed_tailored_job(api_client)
    first = api_client.post(
        f"/api/job-descriptions/{job_description_id}/generated"
    ).json()
    second = api_client.post(
        f"/api/job-descriptions/{job_description_id}/generated"
    ).json()
    first.pop("created_at")
    second.pop("created_at")
    assert first == second


def test_generated_analysis_reports_measured_checks(api_client: TestClient):
    job_description_id = seed_tailored_job(api_client)
    api_client.post(f"/api/job-descriptions/{job_description_id}/generated")

    analysis = api_client.get(
        f"/api/job-descriptions/{job_description_id}/generated/analysis"
    )
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["page_count"] == 1
    assert body["pdf_text_extraction"] is True
    assert body["single_column"] is True
    assert body["standard_headings"] is True
    assert body["critical_info_in_body"] is True
    assert body["unexpected_tables"] == 0
    assert body["unexpected_graphics"] == 0
    assert body["required_keyword_coverage"] == 1.0
    assert isinstance(body["warnings"], list)
    assert isinstance(body["unsupported_requirements"], list)
    assert "ats_score" not in body


def test_generated_analysis_missing_before_generation_is_not_found(
    api_client: TestClient,
):
    resp = api_client.get("/api/job-descriptions/jd-missing/generated/analysis")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_generate_returns_structured_pdf_validation_failed(services: dict, api_client):
    job_description_id = seed_tailored_job(api_client)
    failing_service = GenerationService(
        tailored_repository=services["tailoring_service"]._tailored,
        generated_repository=InMemoryRepository(),
        storage=LocalStorageService(Path("unused")),
        compiler=FakeCompiler(),
        validator=FailingValidator(),
        ats=services["generation_service"]._ats,
    )
    app.dependency_overrides[get_generation_service] = lambda: failing_service
    try:
        resp = api_client.post(
            f"/api/job-descriptions/{job_description_id}/generated"
        )
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "PDF_VALIDATION_FAILED"
        assert resp.json()["error"]["message"]
    finally:
        app.dependency_overrides[get_generation_service] = services[
            "generation_service"
        ]