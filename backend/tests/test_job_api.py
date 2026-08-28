import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_analysis_service, get_job_service
from app.domain.jobs import JOB_TYPE_ANALYZE
from app.llm.fixture import FixtureLLMProvider
from app.main import app
from app.repositories.in_memory import InMemoryRepository
from app.services.analysis import AnalysisService
from app.services.jobs import JobService

SAMPLE_JD = """\
Role: Senior Backend Engineer
Location: Remote

Responsibilities:
- Lead the design of the API platform

Requirements:
- Must have 5+ years of Python experience
- Experience with FastAPI
- Strong communication skills preferred
- Experience with Docker preferred
"""


class CountingProvider(FixtureLLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def generate_structured(self, *, prompt, output_schema):
        self.calls += 1
        return super().generate_structured(prompt=prompt, output_schema=output_schema)


@pytest.fixture
def job_service() -> JobService:
    return JobService(InMemoryRepository())


@pytest.fixture
def analysis_service(job_service: JobService) -> AnalysisService:
    return AnalysisService(
        jd_repository=InMemoryRepository(),
        analysis_repository=InMemoryRepository(),
        llm_provider=FixtureLLMProvider(),
    )


@pytest.fixture
def api_client(job_service: JobService, analysis_service: AnalysisService) -> TestClient:
    app.dependency_overrides[get_job_service] = lambda: job_service
    app.dependency_overrides[get_analysis_service] = lambda: analysis_service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def submit_job(client: TestClient, jd_text: str = SAMPLE_JD) -> dict:
    resp = client.post("/api/job-descriptions", json={"jd_text": jd_text})
    assert resp.status_code == 201
    return resp.json()


def test_submit_job_description_returns_pending_job(api_client):
    body = submit_job(api_client)
    assert body["status"] == "PENDING"
    assert body["job_description_id"]
    assert body["job_id"]


def test_poll_job_shows_completion_after_background_analysis(api_client):
    submitted = submit_job(api_client)

    poll = api_client.get(f"/api/jobs/{submitted['job_id']}")
    assert poll.status_code == 200
    job = poll.json()
    assert job["type"] == JOB_TYPE_ANALYZE
    assert job["status"] == "SUCCEEDED"
    assert job["error"] is None
    assert job["result"]["role"] == "Senior Backend Engineer"


def test_analysis_endpoint_returns_classified_requirements(api_client):
    submitted = submit_job(api_client)

    analysis = api_client.get(f"/api/job-descriptions/{submitted['job_description_id']}/analysis")
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["role"] == "Senior Backend Engineer"
    assert body["seniority"] == "Senior"
    assert body["requirements"]

    required = [r for r in body["requirements"] if r["category"] == "REQUIRED"]
    responsibilities = [r for r in body["requirements"] if r["category"] == "RESPONSIBILITY"]
    soft_skills = [r for r in body["requirements"] if r["category"] == "SOFT_SKILL"]
    preferred = [r for r in body["requirements"] if r["category"] == "PREFERRED"]
    assert any("fastapi" in r["requirement"].lower() and r["importance"] == "MEDIUM" for r in required)
    assert any("lead the design" in r["requirement"].lower() for r in responsibilities)
    assert any("communication" in r["requirement"].lower() for r in soft_skills)
    assert any("docker" in r["requirement"].lower() for r in preferred)


def test_analysis_refetches_without_re_running_llm():
    provider = CountingProvider()
    job_service = JobService(InMemoryRepository())
    analysis_service = AnalysisService(
        jd_repository=InMemoryRepository(),
        analysis_repository=InMemoryRepository(),
        llm_provider=provider,
    )
    app.dependency_overrides[get_job_service] = lambda: job_service
    app.dependency_overrides[get_analysis_service] = lambda: analysis_service
    try:
        with TestClient(app) as client:
            submitted = submit_job(client)
            jd_id = submitted["job_description_id"]

            first = client.get(f"/api/job-descriptions/{jd_id}/analysis").json()
            second = client.get(f"/api/job-descriptions/{jd_id}/analysis").json()

            assert first == second
            assert provider.calls == 1
    finally:
        app.dependency_overrides.clear()


def test_job_description_endpoint_roundtrips_untrusted_input(api_client):
    dangerous = "Role: Engineer\n$(rm -rf /)\n\\usepackage{evil} & % $ # _ { }\n- Python\n"
    submitted = submit_job(api_client, dangerous)

    stored = api_client.get(f"/api/job-descriptions/{submitted['job_description_id']}")
    assert stored.status_code == 200
    jd_text = stored.json()["jd_text"]
    assert "$(rm -rf /)" in jd_text
    assert "\\usepackage{evil}" in jd_text
    assert "& % $ # _ { }" in jd_text


def test_submit_blank_job_description_returns_validation_error(api_client):
    resp = api_client.post("/api/job-descriptions", json={"jd_text": "   \n "})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_missing_analysis_returns_not_found(api_client):
    resp = api_client.get("/api/job-descriptions/missing/analysis")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_get_missing_job_returns_not_found(api_client):
    resp = api_client.get("/api/jobs/missing")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_list_jobs_filters_by_type_and_job_description_id(api_client):
    first = submit_job(api_client)
    second = submit_job(api_client)

    all_jobs = api_client.get("/api/jobs")
    assert all_jobs.status_code == 200
    assert {job["id"] for job in all_jobs.json()} == {first["job_id"], second["job_id"]}

    analyzed = api_client.get("/api/jobs", params={"type": "ANALYZE"})
    assert {job["id"] for job in analyzed.json()} == {
        first["job_id"],
        second["job_id"],
    }

    for_jd = api_client.get(
        "/api/jobs",
        params={"type": "ANALYZE", "job_description_id": first["job_description_id"]},
    )
    assert [job["id"] for job in for_jd.json()] == [first["job_id"]]


def test_list_jobs_is_newest_first(api_client):
    submit_job(api_client, "Role: Engineer A\n- Must have Python\n")
    submit_job(api_client, "Role: Engineer B\n- Must have Python\n")

    jobs = api_client.get("/api/jobs", params={"type": "ANALYZE"}).json()
    assert jobs[0]["result"]["role"] == "Engineer B"
    assert jobs[1]["result"]["role"] == "Engineer A"