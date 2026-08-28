import shutil
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.domain.resume import Experience, PersonalInformation, Resume
from app.main import app
from app.services.health import HealthService, get_health_service

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _psycopg_url(postgres: PostgresContainer) -> str:
    return postgres.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_migrations_apply_to_postgres() -> None:
    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            table_names = set(
                conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).scalars()
            )
        assert version == "0005"
        assert "resumes" in table_names
        assert "resume_versions" in table_names
        assert "tailored_resumes" in table_names
        assert "generated_resumes" in table_names


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_sqlalchemy_resume_repository_roundtrip() -> None:
    from sqlalchemy.orm import sessionmaker

    from app.repositories.resume import SqlAlchemyResumeRepository

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        repo = SqlAlchemyResumeRepository(sessionmaker(bind=create_engine(url)))
        created = repo.create(_resume())
        fetched = repo.get(created.id)
        assert fetched == created
        assert fetched.personal_information.full_name == "Ada Lovelace"

        listed = repo.list()
        assert [r.id for r in listed] == [created.id]

        updated = repo.update(
            created.id,
            Resume.model_validate({**created.model_dump(exclude={"id"}), "summary": "Updated"}),
        )
        assert updated.summary == "Updated"
        assert repo.get(created.id).summary == "Updated"


def _resume() -> Resume:
    return Resume(
        personal_information=PersonalInformation(full_name="Ada Lovelace"),
        summary="Deterministic document pipelines.",
        experience=[Experience(company="Analytical Engines Ltd", title="Engineer", start_date="2021-03")],
    )


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_health_reports_database_ok() -> None:
    from fastapi.testclient import TestClient

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        app.dependency_overrides[get_health_service] = lambda: HealthService(
            create_engine(url)
        )
        with TestClient(app) as client:
            body = client.get("/api/health").json()
        app.dependency_overrides.clear()

    assert body["database"]["status"] == "ok"


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_job_description_analysis_and_job_persist() -> None:
    from sqlalchemy.orm import Session

    from app.llm.fixture import FixtureLLMProvider
    from app.models import Job, JobAnalysis, JobDescription
    from app.repositories import mappers
    from app.repositories.sqlalchemy import SqlAlchemyRepository
    from app.services.analysis import AnalysisService
    from app.services.jobs import JobService

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        session = Session(engine)
        jd_service = AnalysisService(
            jd_repository=SqlAlchemyRepository(
                session,
                JobDescription,
                mappers.job_description_to_row,
                mappers.job_description_from_row,
            ),
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            llm_provider=FixtureLLMProvider(),
        )
        job_service = JobService(
            SqlAlchemyRepository(session, Job, mappers.job_to_row, mappers.job_from_row)
        )

        job_description = jd_service.create_job_description(
            company="Acme", role=None, location=None, jd_text="Role: Engineer\n- Must have Python\n"
        )
        analysis = jd_service.analyze_job(job_description.id)
        job = job_service.create("ANALYZE", {"job_description_id": job_description.id})

        session.commit()

        loaded_jd = session.get(JobDescription, job_description.id)
        loaded_analysis = session.get(JobAnalysis, job_description.id)
        loaded_job = session.get(Job, job.id)

        assert loaded_jd is not None
        assert loaded_analysis is not None
        assert loaded_analysis.role == analysis.role
        assert loaded_analysis.requirements[0]["requirement"] == "Must have Python"
        assert loaded_job is not None
        assert loaded_job.status == "PENDING"


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_match_result_persists_to_postgres() -> None:
    from sqlalchemy.orm import Session, sessionmaker

    from app.domain.resume import Experience, PersonalInformation, Resume
    from app.llm.fixture import FixtureLLMProvider
    from app.models import JobAnalysis, JobDescription, MatchResultRow
    from app.repositories import mappers
    from app.repositories.resume import SqlAlchemyResumeRepository
    from app.repositories.sqlalchemy import SqlAlchemyRepository
    from app.services.analysis import AnalysisService
    from app.services.matching import MatchingService

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        session_factory = sessionmaker(bind=engine)
        session = Session(engine)

        jd_service = AnalysisService(
            jd_repository=SqlAlchemyRepository(
                session,
                JobDescription,
                mappers.job_description_to_row,
                mappers.job_description_from_row,
            ),
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            llm_provider=FixtureLLMProvider(),
        )
        job_description = jd_service.create_job_description(
            company="Acme",
            role=None,
            location=None,
            jd_text="Role: Engineer\n- Must have Python\n- Must have FastAPI\n",
        )
        jd_service.analyze_job(job_description.id)

        resume_repo = SqlAlchemyResumeRepository(session_factory)
        resume = resume_repo.create(
            Resume(
                personal_information=PersonalInformation(full_name="Ada Lovelace"),
                skills={"languages": ["Python"], "frameworks": ["FastAPI"]},
                experience=[
                    Experience(
                        company="Acme",
                        title="Engineer",
                        start_date="2021-03",
                        bullets=["Shipped Python services"],
                    )
                ],
            )
        )

        matching = MatchingService(
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            match_repository=SqlAlchemyRepository(
                session,
                MatchResultRow,
                mappers.match_result_to_row,
                mappers.match_result_from_row,
            ),
        )
        matching.match_for_job(job_description.id, resume)

        session.commit()
        loaded = session.get(MatchResultRow, job_description.id)
        assert loaded is not None
        assert loaded.resume_id == resume.id
        assert loaded.matches[0]["status"] == "STRONG_MATCH"
        assert loaded.matches[1]["status"] == "PARTIAL_MATCH"


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_match_endpoint_end_to_end_on_postgres() -> None:
    """The HTTP /match route against real Postgres-backed services.

    Covers the wiring behind commit "fix T4 match persistence": submit a
    resume and a job description over HTTP (background ANALYZE included), then
    match over HTTP and re-fetch to confirm a stable persisted row.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session, sessionmaker

    from app.dependencies import (
        get_analysis_service,
        get_job_service,
        get_matching_service,
    )
    from app.llm.fixture import FixtureLLMProvider
    from app.models import Job, JobAnalysis, JobDescription, MatchResultRow
    from app.repositories import mappers
    from app.repositories.resume import SqlAlchemyResumeRepository
    from app.repositories.sqlalchemy import SqlAlchemyRepository
    from app.services.analysis import AnalysisService
    from app.services.jobs import JobService
    from app.services.matching import MatchingService
    from app.services.resume import ResumeService, get_resume_service

    resume_payload = {
        "schema_version": 1,
        "personal_information": {"full_name": "Ada Lovelace"},
        "skills": {"languages": ["Python"], "frameworks": ["FastAPI"]},
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2021-03",
                "bullets": ["Shipped Python services"],
            }
        ],
    }

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        session = Session(engine)
        session_factory = sessionmaker(bind=engine)

        analysis_service = AnalysisService(
            jd_repository=SqlAlchemyRepository(
                session,
                JobDescription,
                mappers.job_description_to_row,
                mappers.job_description_from_row,
            ),
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            llm_provider=FixtureLLMProvider(),
        )
        job_service = JobService(
            SqlAlchemyRepository(session, Job, mappers.job_to_row, mappers.job_from_row)
        )
        matching_service = MatchingService(
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            match_repository=SqlAlchemyRepository(
                session,
                MatchResultRow,
                mappers.match_result_to_row,
                mappers.match_result_from_row,
            ),
        )
        resume_service = ResumeService(SqlAlchemyResumeRepository(session_factory))

        app.dependency_overrides[get_job_service] = lambda: job_service
        app.dependency_overrides[get_analysis_service] = lambda: analysis_service
        app.dependency_overrides[get_matching_service] = lambda: matching_service
        app.dependency_overrides[get_resume_service] = lambda: resume_service

        try:
            with TestClient(app) as client:
                resume_resp = client.post("/api/resumes", json=resume_payload)
                assert resume_resp.status_code == 201
                resume_id = resume_resp.json()["id"]

                submitted = client.post(
                    "/api/job-descriptions",
                    json={
                        "jd_text": "Role: Engineer\n- Must have Python\n- Must have FastAPI\n"
                    },
                )
                assert submitted.status_code == 201
                job_description_id = submitted.json()["job_description_id"]

                url_match = (
                    f"/api/job-descriptions/{job_description_id}/match"
                )
                first = client.get(url_match, params={"resume_id": resume_id})
                assert first.status_code == 200
                body = first.json()
                by_requirement = {m["requirement"]: m for m in body["matches"]}
                assert by_requirement["Must have Python"]["status"] == "STRONG_MATCH"
                assert by_requirement["Must have FastAPI"]["status"] == "PARTIAL_MATCH"

                second = client.get(url_match, params={"resume_id": resume_id})
                assert second.status_code == 200
                assert second.json() == body
        finally:
            app.dependency_overrides.clear()


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_generated_resume_persists_to_postgres() -> None:
    """The synchronous GENERATE flow against real Postgres-backed services.

    Submits a resume and a job description over HTTP (background ANALYZE),
    matches, runs a TAILOR job, then generates the document synchronously and
    asserts the GeneratedResume row is persisted pinned to the ResumeVersion.
    """
    import tempfile
    from pathlib import Path

    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session, sessionmaker

    from app.dependencies import (
        get_analysis_service,
        get_generation_service,
        get_job_service,
        get_matching_service,
        get_tailoring_service,
    )
    from app.domain.generated import GeneratedResume
    from app.llm.fixture import FixtureLLMProvider
    from app.models import (
        GeneratedResumeRow,
        Job,
        JobAnalysis,
        JobDescription,
        MatchResultRow,
        ResumeVersionRow,
        TailoredResumeRow,
    )
    from app.repositories import mappers
    from app.repositories.resume import SqlAlchemyResumeRepository
    from app.repositories.sqlalchemy import SqlAlchemyRepository
    from app.services.analysis import AnalysisService
    from app.services.generation import GenerationService
    from app.services.jobs import JobService
    from app.services.matching import MatchingService
    from app.services.resume import ResumeService, get_resume_service
    from app.services.tailoring import TailoringService
    from app.storage.local import LocalStorageService

    class FakeCompiler:
        def compile(self, tex: str, work_dir: Path) -> Path:
            pdf = work_dir / "main.pdf"
            pdf.write_bytes(b"%PDF-1.4 fake generated output")
            return pdf

    resume_payload = {
        "schema_version": 1,
        "personal_information": {"full_name": "Ada Lovelace"},
        "summary": "Backend engineer who builds API platforms.",
        "skills": {"languages": ["Python"], "frameworks": ["FastAPI"]},
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2021-03",
                "bullets": ["Built the ordering API with FastAPI"],
            }
        ],
    }

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        session = Session(engine)
        session_factory = sessionmaker(bind=engine)

        analysis_service = AnalysisService(
            jd_repository=SqlAlchemyRepository(
                session,
                JobDescription,
                mappers.job_description_to_row,
                mappers.job_description_from_row,
            ),
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            llm_provider=FixtureLLMProvider(),
        )
        job_service = JobService(
            SqlAlchemyRepository(session, Job, mappers.job_to_row, mappers.job_from_row)
        )
        matching_service = MatchingService(
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            match_repository=SqlAlchemyRepository(
                session,
                MatchResultRow,
                mappers.match_result_to_row,
                mappers.match_result_from_row,
            ),
        )
        resume_repo = SqlAlchemyResumeRepository(session_factory)
        resume_service = ResumeService(resume_repo)
        tailored_repo = SqlAlchemyRepository(
            session,
            TailoredResumeRow,
            mappers.tailored_resume_to_row,
            mappers.tailored_resume_from_row,
        )
        tailoring_service = TailoringService(
            version_repository=SqlAlchemyRepository(
                session,
                ResumeVersionRow,
                mappers.resume_version_to_row,
                mappers.resume_version_from_row,
            ),
            tailored_repository=tailored_repo,
            resume_repository=resume_repo,
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            match_repository=SqlAlchemyRepository(
                session,
                MatchResultRow,
                mappers.match_result_to_row,
                mappers.match_result_from_row,
            ),
            llm_provider=FixtureLLMProvider(),
        )
        generation_service = GenerationService(
            tailored_repository=tailored_repo,
            generated_repository=SqlAlchemyRepository(
                session,
                GeneratedResumeRow,
                mappers.generated_resume_to_row,
                mappers.generated_resume_from_row,
            ),
            storage=LocalStorageService(Path(tempfile.mkdtemp(prefix="ats-gen-"))),
            compiler=FakeCompiler(),
        )

        app.dependency_overrides[get_job_service] = lambda: job_service
        app.dependency_overrides[get_analysis_service] = lambda: analysis_service
        app.dependency_overrides[get_matching_service] = lambda: matching_service
        app.dependency_overrides[get_resume_service] = lambda: resume_service
        app.dependency_overrides[get_tailoring_service] = lambda: tailoring_service
        app.dependency_overrides[get_generation_service] = lambda: generation_service

        try:
            with TestClient(app) as client:
                resume_resp = client.post("/api/resumes", json=resume_payload)
                assert resume_resp.status_code == 201
                resume_id = resume_resp.json()["id"]

                submitted = client.post(
                    "/api/job-descriptions",
                    json={"jd_text": "Role: Engineer\n- Must have FastAPI\n"},
                )
                assert submitted.status_code == 201
                job_description_id = submitted.json()["job_description_id"]

                client.get(
                    f"/api/job-descriptions/{job_description_id}/match",
                    params={"resume_id": resume_id},
                )
                tailor_resp = client.post(
                    f"/api/resumes/{resume_id}/tailor",
                    json={"job_description_id": job_description_id},
                )
                assert tailor_resp.status_code == 201
                tailor_job = client.get(f"/api/jobs/{tailor_resp.json()['job_id']}")
                assert tailor_job.json()["status"] == "SUCCEEDED"

                generate_resp = client.post(
                    f"/api/job-descriptions/{job_description_id}/generated"
                )
                assert generate_resp.status_code == 201
                body = generate_resp.json()
                assert body["latex_key"] == f"latex/{job_description_id}.tex"
                assert body["pdf_key"] == f"pdf/{job_description_id}.pdf"

                pdf = client.get(
                    f"/api/job-descriptions/{job_description_id}/generated/pdf"
                )
                assert pdf.status_code == 200
                assert pdf.content.startswith(b"%PDF")
                latex = client.get(
                    f"/api/job-descriptions/{job_description_id}/generated/latex"
                )
                assert latex.status_code == 200
                assert latex.content.startswith(b"\\documentclass")

                generated_row = session.get(
                    GeneratedResumeRow, job_description_id
                )
                assert generated_row is not None
                assert generated_row.resume_version_id == body["resume_version_id"]
                assert generated_row.resume_id == resume_id
                stored = GeneratedResume.model_validate(generated_row.data)
                assert stored.job_description_id == job_description_id
        finally:
            app.dependency_overrides.clear()


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker unavailable")
def test_tailor_endpoint_end_to_end_on_postgres() -> None:
    """The HTTP tailoring flow against real Postgres-backed services.

    Submits a resume and a job description over HTTP (background ANALYZE
    included), matches, then runs a TAILOR job (background) and asserts the
    Tailored Resume is persisted, pinned to a ResumeVersion row, and that the
    Master Resume row is never mutated (ADR-0004).
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session, sessionmaker

    from app.dependencies import (
        get_analysis_service,
        get_job_service,
        get_matching_service,
        get_tailoring_service,
    )
    from app.domain.resume import Resume
    from app.llm.fixture import FixtureLLMProvider
    from app.models import (
        Job,
        JobAnalysis,
        JobDescription,
        MatchResultRow,
        ResumeVersionRow,
        TailoredResumeRow,
    )
    from app.repositories import mappers
    from app.repositories.resume import SqlAlchemyResumeRepository
    from app.repositories.sqlalchemy import SqlAlchemyRepository
    from app.services.analysis import AnalysisService
    from app.services.jobs import JobService
    from app.services.matching import MatchingService
    from app.services.resume import ResumeService, get_resume_service
    from app.services.tailoring import TailoringService

    resume_payload = {
        "schema_version": 1,
        "personal_information": {"full_name": "Ada Lovelace"},
        "summary": "Backend engineer who builds API platforms.",
        "skills": {"languages": ["Python"], "frameworks": ["FastAPI"]},
        "experience": [
            {
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2021-03",
                "bullets": ["Built the ordering API with FastAPI"],
            }
        ],
    }

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = _psycopg_url(postgres)
        command.upgrade(_alembic_config(url), "head")

        engine = create_engine(url)
        session = Session(engine)
        session_factory = sessionmaker(bind=engine)

        analysis_service = AnalysisService(
            jd_repository=SqlAlchemyRepository(
                session,
                JobDescription,
                mappers.job_description_to_row,
                mappers.job_description_from_row,
            ),
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            llm_provider=FixtureLLMProvider(),
        )
        job_service = JobService(
            SqlAlchemyRepository(session, Job, mappers.job_to_row, mappers.job_from_row)
        )
        matching_service = MatchingService(
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            match_repository=SqlAlchemyRepository(
                session,
                MatchResultRow,
                mappers.match_result_to_row,
                mappers.match_result_from_row,
            ),
        )
        resume_repo = SqlAlchemyResumeRepository(session_factory)
        resume_service = ResumeService(resume_repo)
        tailoring_service = TailoringService(
            version_repository=SqlAlchemyRepository(
                session,
                ResumeVersionRow,
                mappers.resume_version_to_row,
                mappers.resume_version_from_row,
            ),
            tailored_repository=SqlAlchemyRepository(
                session,
                TailoredResumeRow,
                mappers.tailored_resume_to_row,
                mappers.tailored_resume_from_row,
            ),
            resume_repository=resume_repo,
            analysis_repository=SqlAlchemyRepository(
                session,
                JobAnalysis,
                mappers.job_analysis_to_row,
                mappers.job_analysis_from_row,
            ),
            match_repository=SqlAlchemyRepository(
                session,
                MatchResultRow,
                mappers.match_result_to_row,
                mappers.match_result_from_row,
            ),
            llm_provider=FixtureLLMProvider(),
        )

        app.dependency_overrides[get_job_service] = lambda: job_service
        app.dependency_overrides[get_analysis_service] = lambda: analysis_service
        app.dependency_overrides[get_matching_service] = lambda: matching_service
        app.dependency_overrides[get_resume_service] = lambda: resume_service
        app.dependency_overrides[get_tailoring_service] = lambda: tailoring_service

        try:
            with TestClient(app) as client:
                resume_resp = client.post("/api/resumes", json=resume_payload)
                assert resume_resp.status_code == 201
                resume_id = resume_resp.json()["id"]

                submitted = client.post(
                    "/api/job-descriptions",
                    json={"jd_text": "Role: Engineer\n- Must have FastAPI\n"},
                )
                assert submitted.status_code == 201
                job_description_id = submitted.json()["job_description_id"]

                match_resp = client.get(
                    f"/api/job-descriptions/{job_description_id}/match",
                    params={"resume_id": resume_id},
                )
                assert match_resp.status_code == 200

                tailor_resp = client.post(
                    f"/api/resumes/{resume_id}/tailor",
                    json={"job_description_id": job_description_id},
                )
                assert tailor_resp.status_code == 201
                job_id = tailor_resp.json()["job_id"]
                job = client.get(f"/api/jobs/{job_id}")
                assert job.json()["status"] == "SUCCEEDED"

                tailored = client.get(
                    f"/api/job-descriptions/{job_description_id}/tailored"
                )
                assert tailored.status_code == 200
                body = tailored.json()
                assert body["resume_version_id"]
                assert body["experience"][0]["bullets"] == [
                    "Built the ordering API with FastAPI"
                ]
                assert all(c["source_evidence_ids"] for c in body["changes"])

                version_row = session.get(ResumeVersionRow, body["resume_version_id"])
                assert version_row is not None
                assert version_row.resume_id == resume_id
                snapshot = Resume.model_validate(
                    {**version_row.data, "id": resume_id}
                )
                assert snapshot.summary == "Backend engineer who builds API platforms."

                tailored_row = session.get(TailoredResumeRow, job_description_id)
                assert tailored_row is not None
                assert tailored_row.resume_version_id == body["resume_version_id"]

                # the live master row is unchanged by tailoring
                fetched_master = resume_repo.get(resume_id)
                assert fetched_master.summary == "Backend engineer who builds API platforms."
                assert fetched_master.experience[0].bullets == [
                    "Built the ordering API with FastAPI"
                ]
        finally:
            app.dependency_overrides.clear()