import pytest

from app.domain.analysis import (
    Importance,
    JobRequirement,
    LLMJobAnalysis,
    RequirementCategory,
)
from app.errors import LLMValidationFailed, ResourceValidationError
from app.llm.fixture import FixtureLLMProvider
from app.repositories.in_memory import InMemoryRepository
from app.services.analysis import AnalysisService

SAMPLE_JD = """\
Role: Senior Backend Engineer
Location: Remote

Responsibilities:
- Lead the design of the API platform
- Mentor junior engineers

Requirements:
- Must have 5+ years of Python experience
- Experience with FastAPI
- Strong communication skills preferred
- Prior finance domain experience is a plus
- Experience with Docker preferred
"""


def make_service(provider: FixtureLLMProvider | None = None) -> AnalysisService:
    return AnalysisService(
        jd_repository=InMemoryRepository(),
        analysis_repository=InMemoryRepository(),
        llm_provider=provider or FixtureLLMProvider(),
    )


def test_analysis_extracts_role_seniority_and_requirements():
    service = make_service()
    analysis = service.analyze(SAMPLE_JD)

    assert analysis.role == "Senior Backend Engineer"
    assert analysis.seniority == "Senior"
    assert len(analysis.requirements) == 7


def test_analysis_classifies_requirements():
    service = make_service()
    analysis = service.analyze(SAMPLE_JD)

    by_category: dict[RequirementCategory, list[str]] = {}
    for requirement in analysis.requirements:
        by_category.setdefault(requirement.category, []).append(requirement.requirement)

    assert "Experience with FastAPI" in by_category[RequirementCategory.REQUIRED]
    assert "Lead the design of the API platform" in by_category[RequirementCategory.RESPONSIBILITY]
    assert "Mentor junior engineers" in by_category[RequirementCategory.RESPONSIBILITY]
    assert (
        "Strong communication skills preferred"
        in by_category[RequirementCategory.SOFT_SKILL]
    )
    assert (
        "Prior finance domain experience is a plus"
        in by_category[RequirementCategory.DOMAIN]
    )
    assert "Experience with Docker preferred" in by_category[RequirementCategory.PREFERRED]
    assert (
        "Must have 5+ years of Python experience"
        in by_category[RequirementCategory.SENIORITY]
    )


def test_analysis_assigns_importance():
    service = make_service()
    analysis = service.analyze(SAMPLE_JD)

    by_requirement = {r.requirement: r for r in analysis.requirements}
    assert by_requirement["Must have 5+ years of Python experience"].importance == Importance.HIGH
    assert by_requirement["Experience with FastAPI"].importance == Importance.MEDIUM
    assert (
        by_requirement["Prior finance domain experience is a plus"].importance
        == Importance.LOW
    )


def test_analysis_normalizes_whitespace_and_dedupes():
    service = make_service()
    analysis = service.analyze("Role:  Backend   Engineer\n\n-  Must  have  Python\n- Must have Python")

    assert analysis.role == "Backend Engineer"
    assert len(analysis.requirements) == 1
    assert analysis.requirements[0].requirement == "Must have Python"


def test_analysis_preserves_jd_context():
    service = make_service()
    analysis = service.analyze(SAMPLE_JD)

    requirement = next(
        r for r in analysis.requirements if r.requirement == "Must have 5+ years of Python experience"
    )
    assert requirement.context == "Must have 5+ years of Python experience"
    assert "5+ years" in requirement.context


def test_analysis_retries_once_on_invalid_output():
    provider = FixtureLLMProvider(
        responses=[
            {
                "role": "Engineer",
                "seniority": "Senior",
                "requirements": [
                    {
                        "requirement": "Python",
                        "category": "NOT_A_CATEGORY",
                        "importance": "HIGH",
                        "context": "Python",
                    }
                ],
            },
            LLMJobAnalysis(
                role="Engineer",
                seniority="Senior",
                requirements=[
                    JobRequirement(
                        requirement="Python",
                        category=RequirementCategory.REQUIRED,
                        importance=Importance.HIGH,
                        context="Python",
                    )
                ],
            ),
        ]
    )
    service = make_service(provider)

    analysis = service.analyze("Role: Engineer\n- Python\n")
    assert analysis.role == "Engineer"
    assert len(analysis.requirements) == 1
    assert analysis.requirements[0].category == RequirementCategory.REQUIRED


def test_analysis_fails_cleanly_when_output_keeps_failing():
    provider = FixtureLLMProvider(responses=[{"bad": "output"}, {"bad": "output"}])
    service = make_service(provider)

    with pytest.raises(LLMValidationFailed):
        service.analyze("Role: Engineer\n- Python\n")


def test_create_job_description_rejects_blank_text():
    service = make_service()
    with pytest.raises(ResourceValidationError):
        service.create_job_description(
            company=None, role=None, location=None, jd_text="   \n  "
        )


def test_create_job_description_keeps_text_as_untrusted_data():
    service = make_service()
    dangerous = "Role: Engineer\n$(rm -rf /)\n\\usepackage{evil} & % $ # _ { }\n- Python & Go\n"
    job_description = service.create_job_description(
        company=None, role=None, location=None, jd_text=dangerous
    )

    assert "$(rm -rf /)" in job_description.jd_text
    assert "\\usepackage{evil}" in job_description.jd_text
    assert "& % $ # _ { }" in job_description.jd_text

    analysis = service.analyze(job_description.jd_text)
    assert any("Python & Go" in r.requirement for r in analysis.requirements)