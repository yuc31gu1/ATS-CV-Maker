import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_analysis_service,
    get_job_service,
    get_matching_service,
    get_tailoring_service,
)
from app.domain.jobs import JOB_TYPE_TAILOR
from app.llm.fixture import FixtureLLMProvider
from app.main import app
from app.repositories.in_memory import InMemoryRepository
from app.repositories.resume import InMemoryResumeRepository
from app.services.analysis import AnalysisService
from app.services.jobs import JobService
from app.services.matching import MatchingService
from app.services.resume import ResumeService, get_resume_service
from app.services.tailoring import TailoringService

SAMPLE_JD = """\
Role: Senior Backend Engineer
Location: Remote

Responsibilities:
- Lead the design of the API platform

Requirements:
- Experience with FastAPI
"""


def resume_payload() -> dict:
    return {
        "schema_version": 1,
        "personal_information": {"full_name": "Ada Lovelace"},
        "summary": "Backend engineer who builds API platforms.",
        "skills": {"frameworks": ["FastAPI"]},
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2021-03",
                "bullets": ["Built the ordering API with FastAPI", "Wrote UI copy"],
            }
        ],
    }


@pytest.fixture
def services() -> dict:
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
    tailoring_service = TailoringService(
        version_repository=InMemoryRepository(),
        tailored_repository=InMemoryRepository(),
        resume_repository=resume_service._repository,
        analysis_repository=analysis_repo,
        match_repository=match_repo,
        llm_provider=FixtureLLMProvider(),
    )

    app.dependency_overrides[get_job_service] = lambda: job_service
    app.dependency_overrides[get_analysis_service] = lambda: analysis_service
    app.dependency_overrides[get_matching_service] = lambda: matching_service
    app.dependency_overrides[get_resume_service] = lambda: resume_service
    app.dependency_overrides[get_tailoring_service] = lambda: tailoring_service
    return {
        "job_service": job_service,
        "tailoring_service": tailoring_service,
        "resume_service": resume_service,
        "analysis_repo": analysis_repo,
        "match_repo": match_repo,
    }


@pytest.fixture
def api_client(services: dict) -> TestClient:
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def seed_matched_job(client: TestClient) -> dict:
    resume_resp = client.post("/api/resumes", json=resume_payload())
    assert resume_resp.status_code == 201
    resume_id = resume_resp.json()["id"]

    submitted = client.post(
        "/api/job-descriptions", json={"jd_text": SAMPLE_JD}
    )
    assert submitted.status_code == 201
    job_description_id = submitted.json()["job_description_id"]

    match_resp = client.get(
        f"/api/job-descriptions/{job_description_id}/match",
        params={"resume_id": resume_id},
    )
    assert match_resp.status_code == 200
    return {"resume_id": resume_id, "job_description_id": job_description_id}


def submit_and_complete_tailor(client: TestClient, jd_id: str, resume_id: str) -> dict:
    resp = client.post(f"/api/resumes/{resume_id}/tailor", json={"job_description_id": jd_id})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING"
    job = client.get(f"/api/jobs/{body['job_id']}")
    assert job.status_code == 200
    assert job.json()["type"] == JOB_TYPE_TAILOR
    assert job.json()["status"] == "SUCCEEDED"
    assert job.json()["error"] is None
    return body


def test_tailor_job_end_to_end_pins_version_and_persists(api_client, services):
    seeded = seed_matched_job(api_client)
    submit_and_complete_tailor(
        api_client, seeded["job_description_id"], seeded["resume_id"]
    )

    tailored = api_client.get(
        f"/api/job-descriptions/{seeded['job_description_id']}/tailored"
    )
    assert tailored.status_code == 200
    body = tailored.json()
    assert body["job_description_id"] == seeded["job_description_id"]
    assert body["resume_id"] == seeded["resume_id"]
    assert body["resume_version_id"]
    # only evidence substantiating matched requirements survives
    assert body["experience"][0]["bullets"] == ["Built the ordering API with FastAPI"]
    assert [c["key"] for c in body["changes"]] == [
        "summary",
        "experience:0:bullet:0",
    ]
    # every change carries source evidence ids
    assert all(change["source_evidence_ids"] for change in body["changes"])
    # refetch is stable
    assert api_client.get(
        f"/api/job-descriptions/{seeded['job_description_id']}/tailored"
    ).json() == body


def test_tailored_missing_before_tailoring_returns_not_found(api_client):
    resp = api_client.get("/api/job-descriptions/missing/tailored")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_review_decisions_apply_without_mutating_master(api_client, services):
    seeded = seed_matched_job(api_client)
    submit_and_complete_tailor(api_client, seeded["job_description_id"], seeded["resume_id"])

    resp = api_client.post(
        f"/api/job-descriptions/{seeded['job_description_id']}/tailored/decisions",
        json={
            "decisions": [
                {"key": "experience:0:bullet:0", "action": "accept"},
                {"key": "summary", "action": "edit", "text": "Edited summary."},
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    by_key = {c["key"]: c for c in body["changes"]}
    assert by_key["experience:0:bullet:0"]["status"] == "ACCEPTED"
    assert by_key["summary"]["status"] == "EDITED"
    assert body["summary"] == "Edited summary."

    # the master resume is untouched
    master = api_client.get(f"/api/resumes/{seeded['resume_id']}")
    assert master.json()["summary"] == "Backend engineer who builds API platforms."


def test_review_decisions_unknown_change_returns_validation_error(api_client):
    seeded = seed_matched_job(api_client)
    submit_and_complete_tailor(api_client, seeded["job_description_id"], seeded["resume_id"])

    resp = api_client.post(
        f"/api/job-descriptions/{seeded['job_description_id']}/tailored/decisions",
        json={"decisions": [{"key": "nope", "action": "accept"}]},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_regenerate_creates_tailor_job_and_rewrites_change(api_client):
    seeded = seed_matched_job(api_client)
    submit_and_complete_tailor(api_client, seeded["job_description_id"], seeded["resume_id"])
    before = api_client.get(
        f"/api/job-descriptions/{seeded['job_description_id']}/tailored"
    ).json()

    resp = api_client.post(
        f"/api/job-descriptions/{seeded['job_description_id']}/tailored/regenerate",
        json={"change_key": "summary"},
    )
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]
    job = api_client.get(f"/api/jobs/{job_id}")
    assert job.json()["status"] == "SUCCEEDED"

    after = api_client.get(
        f"/api/job-descriptions/{seeded['job_description_id']}/tailored"
    ).json()
    assert after["resume_version_id"] == before["resume_version_id"]
    assert after["summary"] == "Backend engineer who builds API platforms."


def test_tailor_job_fails_cleanly_when_llm_hallucinates(api_client, services):
    from app.domain.tailoring import LLMTailoredOutput, RewrittenBullet

    provider = FixtureLLMProvider(
        responses=[
            LLMTailoredOutput(
                summary="Summary",
                bullets=[
                    RewrittenBullet(
                        evidence_id="experience:0:bullet:0",
                        text="Built the ordering API with FastAPI and Kubernetes",
                        source_evidence_ids=["experience:0:bullet:0"],
                    )
                ],
            )
        ]
    )
    app.dependency_overrides[get_tailoring_service] = lambda: TailoringService(
        version_repository=InMemoryRepository(),
        tailored_repository=InMemoryRepository(),
        resume_repository=services["resume_service"]._repository,
        analysis_repository=services["analysis_repo"],
        match_repository=services["match_repo"],
        llm_provider=provider,
    )
    seeded = seed_matched_job(api_client)
    resp = client_post_tailor(api_client, seeded["job_description_id"], seeded["resume_id"])
    job = api_client.get(f"/api/jobs/{resp['job_id']}")
    assert job.json()["status"] == "FAILED"
    assert job.json()["error"]["code"] == "TAILORING_FAILED"


def client_post_tailor(client: TestClient, jd_id: str, resume_id: str) -> dict:
    resp = client.post(f"/api/resumes/{resume_id}/tailor", json={"job_description_id": jd_id})
    assert resp.status_code == 201
    return resp.json()