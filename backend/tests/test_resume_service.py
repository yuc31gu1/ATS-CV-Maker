import pytest

from app.domain.resume import Resume
from app.errors import InvalidResumeError, NotFoundError
from app.repositories.resume import InMemoryResumeRepository
from app.services.resume import ResumeService


def _payload() -> dict:
    return {
        "schema_version": 1,
        "personal_information": {"full_name": "Ada Lovelace"},
        "summary": "Deterministic document pipelines.",
        "experience": [
            {
                "company": "Analytical Engines Ltd",
                "title": "Engineer",
                "start_date": "2021-03",
                "end_date": "2024-05",
                "bullets": ["Shipped the PDF pipeline"],
            }
        ],
    }


@pytest.fixture
def service() -> ResumeService:
    return ResumeService(InMemoryResumeRepository())


def test_create_assigns_id_and_returns_resume(service) -> None:
    resume = service.create(_payload())
    assert resume.id is not None
    assert resume.personal_information.full_name == "Ada Lovelace"
    assert resume.experience[0].bullets[0] == "Shipped the PDF pipeline"


def test_get_returns_created_resume(service) -> None:
    resume = service.create(_payload())
    fetched = service.get(resume.id)
    assert fetched.id == resume.id
    assert fetched.summary == "Deterministic document pipelines."


def test_list_returns_all_resumes(service) -> None:
    first = service.create(_payload())
    second = service.create({**_payload(), "summary": "Second summary"})
    assert {r.id for r in service.list()} == {first.id, second.id}


def test_update_replaces_resume(service) -> None:
    resume = service.create(_payload())
    updated = service.update(
        resume.id, {**_payload(), "summary": "Rewritten summary"}
    )
    assert updated.summary == "Rewritten summary"
    assert service.get(resume.id).summary == "Rewritten summary"


def test_get_missing_resume_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.get("nope")


def test_update_missing_resume_raises_not_found(service) -> None:
    with pytest.raises(NotFoundError):
        service.update("nope", _payload())


def test_invalid_payload_raises_invalid_resume_error(service) -> None:
    with pytest.raises(InvalidResumeError) as excinfo:
        service.create({**_payload(), "experience": [{"company": ""}]})
    assert excinfo.value.code == "INVALID_RESUME"


def test_schema_version_roundtrips_through_repository(service) -> None:
    resume = service.create({**_payload(), "schema_version": 2})
    assert service.get(resume.id).schema_version == 2


def test_master_resume_is_never_mutated_by_caller(service) -> None:
    resume = service.create(_payload())

    fetched = service.get(resume.id)
    fetched.summary = "MUTATED by tailoring/generation"
    fetched.experience[0].bullets[0] = "MUTATED bullet"

    assert service.get(resume.id).summary == "Deterministic document pipelines."
    assert service.get(resume.id).experience[0].bullets[0] == "Shipped the PDF pipeline"


def test_master_resume_is_never_mutated_by_input_object(service) -> None:
    payload = _payload()
    service.create(payload)
    payload["summary"] = "MUTATED after create"
    assert service.list()[0].summary == "Deterministic document pipelines."


def test_stored_resume_is_a_typed_resume_instance(service) -> None:
    resume = service.create(_payload())
    assert isinstance(service.get(resume.id), Resume)