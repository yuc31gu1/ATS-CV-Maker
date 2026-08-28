import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_analysis_service, get_job_service, get_matching_service
from app.llm.fixture import FixtureLLMProvider
from app.main import app
from app.repositories.in_memory import InMemoryRepository
from app.repositories.resume import InMemoryResumeRepository
from app.services.analysis import AnalysisService
from app.services.jobs import JobService
from app.services.matching import MatchingService
from app.services.resume import ResumeService, get_resume_service

SAMPLE_JD = """\
Role: Senior Backend Engineer
Location: Remote

Responsibilities:
- Lead the design of the API platform

Requirements:
- Experience with FastAPI
- Experience with AWS
- Experience with Docker preferred
- Experience with Flask preferred
- Experience with Django preferred
- Prior finance domain experience is a plus
"""


def resume_payload() -> dict:
    return {
        "schema_version": 1,
        "personal_information": {"full_name": "Ada Lovelace"},
        "skills": {
            "languages": ["Python"],
            "frameworks": ["FastAPI", "Flask"],
            "cloud": ["Amazon Web Services"],
        },
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2021-03",
                "bullets": ["Built the ordering API with FastAPI"],
            }
        ],
        "projects": [{"name": "Analytics", "technologies": ["AWS"]}],
    }


@pytest.fixture
def services() -> dict:
    analysis_repo = InMemoryRepository()
    job_service = JobService(InMemoryRepository())
    analysis_service = AnalysisService(
        jd_repository=InMemoryRepository(),
        analysis_repository=analysis_repo,
        llm_provider=FixtureLLMProvider(),
    )
    matching_service = MatchingService(
        analysis_repository=analysis_repo,
        match_repository=InMemoryRepository(),
    )
    resume_service = ResumeService(InMemoryResumeRepository())

    app.dependency_overrides[get_job_service] = lambda: job_service
    app.dependency_overrides[get_analysis_service] = lambda: analysis_service
    app.dependency_overrides[get_matching_service] = lambda: matching_service
    app.dependency_overrides[get_resume_service] = lambda: resume_service
    return {
        "job_service": job_service,
        "analysis_service": analysis_service,
        "matching_service": matching_service,
        "resume_service": resume_service,
    }


@pytest.fixture
def api_client(services: dict) -> TestClient:
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def submit_job(client: TestClient, jd_text: str = SAMPLE_JD) -> dict:
    resp = client.post("/api/job-descriptions", json={"jd_text": jd_text})
    assert resp.status_code == 201
    return resp.json()


def create_resume(client: TestClient) -> dict:
    resp = client.post("/api/resumes", json=resume_payload())
    assert resp.status_code == 201
    return resp.json()


def test_match_endpoint_assigns_all_four_statuses(api_client):
    resume = create_resume(api_client)
    submitted = submit_job(api_client)

    resp = api_client.get(
        f"/api/job-descriptions/{submitted['job_description_id']}/match",
        params={"resume_id": resume["id"]},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["job_description_id"] == submitted["job_description_id"]
    assert body["resume_id"] == resume["id"]
    by_requirement = {m["requirement"]: m for m in body["matches"]}

    fastapi = by_requirement["Experience with FastAPI"]
    assert fastapi["status"] == "STRONG_MATCH"
    assert fastapi["evidence_ids"] == ["experience:0:bullet:0"]
    assert fastapi["ambiguous"] is False

    aws = by_requirement["Experience with AWS"]
    assert aws["status"] == "STRONG_MATCH"
    assert aws["matched_skill"] == "aws"
    assert aws["evidence_ids"] == ["project:0"]

    flask = by_requirement["Experience with Flask preferred"]
    assert flask["status"] == "PARTIAL_MATCH"
    assert flask["matched_skill"] == "flask"
    assert flask["evidence_ids"] == []

    django = by_requirement["Experience with Django preferred"]
    assert django["status"] == "TRANSFERABLE"
    assert django["ambiguous"] is True

    docker = by_requirement["Experience with Docker preferred"]
    assert docker["status"] == "NO_EVIDENCE"
    assert docker["matched_skill"] == "docker"

    finance = by_requirement["Prior finance domain experience is a plus"]
    assert finance["status"] == "NO_EVIDENCE"
    assert finance["matched_skill"] is None


def test_match_persists_and_returns_identical_result_on_refetch(api_client, services):
    resume = create_resume(api_client)
    submitted = submit_job(api_client)
    url = f"/api/job-descriptions/{submitted['job_description_id']}/match"
    params = {"resume_id": resume["id"]}

    first = api_client.get(url, params=params).json()
    second = api_client.get(url, params=params).json()

    assert first == second
    stored = services["matching_service"].get(submitted["job_description_id"])
    assert stored is not None
    assert stored.job_description_id == submitted["job_description_id"]


def test_match_without_resume_uses_first_master_resume(api_client):
    resume = create_resume(api_client)
    submitted = submit_job(api_client)

    resp = api_client.get(
        f"/api/job-descriptions/{submitted['job_description_id']}/match"
    )
    assert resp.status_code == 200
    assert resp.json()["resume_id"] == resume["id"]


def test_match_without_analysis_returns_not_found(api_client):
    resume = create_resume(api_client)
    resp = api_client.get(
        "/api/job-descriptions/missing/match", params={"resume_id": resume["id"]}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_match_with_unknown_resume_returns_not_found(api_client):
    submit_job(api_client)
    resp = api_client.get(
        "/api/job-descriptions/nope/match", params={"resume_id": "missing-resume"}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_match_without_any_resume_returns_not_found(api_client):
    submit_job(api_client)
    resp = api_client.get("/api/job-descriptions/nope/match")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
    assert "master resume" in resp.json()["error"]["message"]