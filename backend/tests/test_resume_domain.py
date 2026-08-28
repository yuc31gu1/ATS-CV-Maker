import pytest
from pydantic import TypeAdapter, ValidationError

from app.domain.resume import MonthYear, Resume, evidence_ids

month_year_adapter = TypeAdapter(MonthYear)


def test_month_year_parses_iso_format() -> None:
    m = month_year_adapter.validate_python("2024-05")
    assert str(m) == "2024-05"
    assert m.year == 2024
    assert m.month == 5


def test_month_year_renders_consistently() -> None:
    assert month_year_adapter.validate_python("2024-05").render() == "May 2024"
    assert month_year_adapter.validate_python("2020-01").render() == "January 2020"


@pytest.mark.parametrize(
    "raw",
    ["2024-13", "2024-00", "2024", "05/2024", "2024-5", "May 2024", "", "not-a-date"],
)
def test_month_year_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValidationError):
        month_year_adapter.validate_python(raw)


def test_month_year_rejects_non_string() -> None:
    with pytest.raises(ValidationError):
        month_year_adapter.validate_python(2024)


def _resume_payload() -> dict:
    return {
        "schema_version": 1,
        "personal_information": {
            "full_name": "Ada Lovelace",
            "headline": "Software Engineer",
            "email": "ada@example.com",
            "phone": "+1 555 0100",
            "location": "London, UK",
            "website": "https://example.com",
        },
        "summary": "Deterministic document pipelines.",
        "skills": {
            "languages": ["Python", "TypeScript"],
            "frameworks": ["FastAPI"],
            "tools": ["Git", "PostgreSQL"],
        },
        "experience": [
            {
                "company": "Analytical Engines Ltd",
                "title": "Engineer",
                "location": "London",
                "start_date": "2021-03",
                "end_date": "2024-05",
                "summary": "Built the analysis engine.",
                "bullets": [
                    "Designed the matching rules",
                    "Shipped the PDF pipeline",
                ],
            }
        ],
        "education": [
            {
                "school": "University of London",
                "degree": "BSc",
                "field": "Mathematics",
                "start_date": "2016-09",
                "end_date": "2020-06",
            }
        ],
        "projects": [
            {
                "name": "ATS CV Maker",
                "description": "Deterministic resume pipeline.",
                "url": "https://github.com/example/ats-cv-maker",
                "technologies": ["Python", "PostgreSQL"],
                "bullets": ["Produces ATS-safe PDFs"],
            }
        ],
        "certifications": [
            {"name": "AWS Solutions Architect", "issuer": "AWS", "date": "2023-01"}
        ],
    }


def test_resume_accepts_every_spec_section() -> None:
    resume = Resume.model_validate(_resume_payload())
    assert resume.schema_version == 1
    assert resume.personal_information.full_name == "Ada Lovelace"
    assert resume.summary.startswith("Deterministic")
    assert resume.skills["frameworks"] == ["FastAPI"]
    assert resume.experience[0].bullets[1] == "Shipped the PDF pipeline"
    assert resume.education[0].degree == "BSc"
    assert resume.projects[0].name == "ATS CV Maker"
    assert resume.certifications[0].issuer == "AWS"
    assert resume.experience[0].start_date.render() == "March 2021"


def test_resume_forward_compatibility_accepts_unknown_version_and_fields() -> None:
    payload = _resume_payload()
    payload["schema_version"] = 99
    payload["future_section"] = {"unknown": True}
    resume = Resume.model_validate(payload)
    assert resume.schema_version == 99


def test_resume_rejects_malformed_dates() -> None:
    payload = _resume_payload()
    payload["experience"][0]["start_date"] = "March 2021"
    with pytest.raises(ValidationError):
        Resume.model_validate(payload)


def test_resume_rejects_missing_required_section_fields() -> None:
    payload = _resume_payload()
    payload["personal_information"]["email"] = "not-an-email"
    with pytest.raises(ValidationError):
        Resume.model_validate(payload)


def test_evidence_ids_are_deterministic_and_indexed() -> None:
    resume = Resume.model_validate(_resume_payload())
    first = evidence_ids(resume)
    second = evidence_ids(Resume.model_validate(_resume_payload()))
    assert first == second
    assert first["experience:0"] == "Engineer at Analytical Engines Ltd"
    assert first["experience:0:bullet:0"] == "Designed the matching rules"
    assert first["experience:0:bullet:1"] == "Shipped the PDF pipeline"
    assert first["project:0"] == "ATS CV Maker"
    assert first["education:0"] == "BSc at University of London"
    assert first["certification:0"] == "AWS Solutions Architect"


def test_evidence_ids_reflect_content_order() -> None:
    resume = Resume.model_validate(
        {
            "schema_version": 1,
            "personal_information": {"full_name": "Ada Lovelace"},
            "projects": [
                {"name": "First", "description": "d1", "technologies": ["A"]},
                {"name": "Second", "description": "d2", "technologies": ["B"]},
            ],
        }
    )
    ids = evidence_ids(resume)
    assert list(ids) == ["project:0", "project:1"]