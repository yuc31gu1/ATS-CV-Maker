from datetime import UTC, datetime

import pytest

from app.domain.analysis import (
    Importance,
    JobAnalysis,
    JobRequirement,
    RequirementCategory,
)
from app.domain.matching import MatchResult, MatchStatus
from app.domain.resume import (
    Experience,
    PersonalInformation,
    Project,
    Resume,
)
from app.errors import NotFoundError
from app.repositories.in_memory import InMemoryRepository
from app.services.matching import MatchingService


def make_service() -> MatchingService:
    return MatchingService(
        analysis_repository=InMemoryRepository(),
        match_repository=InMemoryRepository(),
    )


def requirement(
    text: str,
    *,
    category: RequirementCategory = RequirementCategory.REQUIRED,
    importance: Importance = Importance.HIGH,
) -> JobRequirement:
    return JobRequirement(
        requirement=text, category=category, importance=importance, context=text
    )


def analysis(*requirements: JobRequirement) -> JobAnalysis:
    return JobAnalysis(
        id="jd-1",
        job_description_id="jd-1",
        role="Backend Engineer",
        requirements=list(requirements),
        created_at=datetime.now(UTC),
    )


def resume(**kwargs) -> Resume:
    defaults = {
        "personal_information": PersonalInformation(full_name="Ada Lovelace"),
        "skills": {},
        "experience": [],
        "projects": [],
    }
    defaults.update(kwargs)
    return Resume(id="resume-1", **defaults)


def test_strong_match_when_skill_listed_and_substantiated_in_experience():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Built the ordering API with FastAPI"],
            )
        ],
    )
    result = service.match(analysis(requirement("Experience with FastAPI")), candidate)

    match = result.matches[0]
    assert match.status == MatchStatus.STRONG_MATCH
    assert match.matched_skill == "fastapi"
    assert match.evidence_ids == ["experience:0:bullet:0"]
    assert match.evidence == ["Built the ordering API with FastAPI"]
    assert match.ambiguous is False


def test_strong_match_when_skill_substantiated_in_project():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI"]},
        projects=[
            Project(name="Ordering service", technologies=["FastAPI"]),
        ],
    )
    result = service.match(analysis(requirement("FastAPI")), candidate)

    assert result.matches[0].status == MatchStatus.STRONG_MATCH
    assert result.matches[0].evidence_ids == ["project:0"]


def test_partial_match_when_skill_only_in_skills():
    service = make_service()
    candidate = resume(skills={"frameworks": ["FastAPI"]})
    result = service.match(analysis(requirement("Experience with FastAPI")), candidate)

    match = result.matches[0]
    assert match.status == MatchStatus.PARTIAL_MATCH
    assert match.matched_skill == "fastapi"
    assert match.evidence_ids == []
    assert match.ambiguous is False


def test_transferable_when_only_adjacent_skill_present():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["Flask"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Built the ordering API with Flask"],
            )
        ],
    )
    result = service.match(analysis(requirement("Experience with FastAPI")), candidate)

    match = result.matches[0]
    assert match.status == MatchStatus.TRANSFERABLE
    assert match.matched_skill == "flask"
    assert match.evidence_ids == []
    assert match.ambiguous is True


def test_no_evidence_when_skill_absent():
    service = make_service()
    candidate = resume(skills={"frameworks": ["FastAPI"]})
    result = service.match(analysis(requirement("Experience with Kafka")), candidate)

    match = result.matches[0]
    assert match.status == MatchStatus.NO_EVIDENCE
    assert match.matched_skill == "kafka"
    assert match.ambiguous is False


def test_no_evidence_when_requirement_has_no_catalog_skill():
    service = make_service()
    candidate = resume()
    result = service.match(
        analysis(requirement("Lead the design of the API platform")), candidate
    )

    match = result.matches[0]
    assert match.status == MatchStatus.NO_EVIDENCE
    assert match.matched_skill is None


def test_synonym_resolution_across_requirement_and_resume():
    service = make_service()
    candidate = resume(
        skills={"cloud": ["Amazon Web Services"]},
        projects=[Project(name="Data lake", technologies=["AWS"])],
    )
    result = service.match(analysis(requirement("Experience with AWS")), candidate)

    match = result.matches[0]
    assert match.status == MatchStatus.STRONG_MATCH
    assert match.matched_skill == "aws"
    assert match.evidence_ids == ["project:0"]


def test_synonym_in_requirement_matches_canonical_resume_skill():
    service = make_service()
    candidate = resume(
        skills={"databases": ["postgresql"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Ran migrations on Postgres"],
            )
        ],
    )
    result = service.match(analysis(requirement("Experience with PostgreSQL")), candidate)

    assert result.matches[0].status == MatchStatus.STRONG_MATCH
    assert result.matches[0].matched_skill == "postgresql"


def test_ambiguous_when_requirement_mentions_multiple_distinct_skills():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Deployed the FastAPI service"],
            )
        ],
    )
    result = service.match(
        analysis(requirement("Experience with FastAPI and Flask")), candidate
    )

    match = result.matches[0]
    assert match.status == MatchStatus.STRONG_MATCH
    assert match.ambiguous is True


def test_multiple_skills_with_one_absent_is_not_ambiguous():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Deployed the FastAPI service"],
            )
        ],
    )
    result = service.match(
        analysis(requirement("Experience with FastAPI and Kubernetes")), candidate
    )

    match = result.matches[0]
    assert match.status == MatchStatus.STRONG_MATCH
    assert match.ambiguous is False


def test_preserves_category_and_importance():
    service = make_service()
    candidate = resume(skills={"frameworks": ["FastAPI"]})
    result = service.match(
        analysis(
            requirement(
                "Experience with FastAPI",
                category=RequirementCategory.REQUIRED,
                importance=Importance.MEDIUM,
            )
        ),
        candidate,
    )

    match = result.matches[0]
    assert match.category == RequirementCategory.REQUIRED
    assert match.importance == Importance.MEDIUM


def test_matching_is_deterministic():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI", "Flask"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Built APIs with FastAPI"],
            )
        ],
    )
    jd = analysis(
        requirement("Experience with FastAPI"),
        requirement("Experience with Flask"),
        requirement("Experience with Docker"),
        requirement("Mentor junior engineers"),
    )

    first = service.match(jd, candidate)
    second = service.match(jd, candidate)

    assert first.matches == second.matches
    assert first.job_description_id == second.job_description_id
    assert first.resume_id == second.resume_id
    statuses = [m.status for m in first.matches]
    assert statuses == [
        MatchStatus.STRONG_MATCH,
        MatchStatus.PARTIAL_MATCH,
        MatchStatus.NO_EVIDENCE,
        MatchStatus.NO_EVIDENCE,
    ]


def test_match_for_job_persists_result_and_resolves_resume():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Built the ordering API with FastAPI"],
            )
        ],
    )
    service._analyses.add(
        "jd-1",
        analysis(requirement("Experience with FastAPI")),
    )

    result = service.match_for_job("jd-1", candidate)
    assert isinstance(result, MatchResult)
    assert result.job_description_id == "jd-1"
    assert result.resume_id == "resume-1"
    assert result.matches[0].status == MatchStatus.STRONG_MATCH

    stored = service.get("jd-1")
    assert stored == result


def test_match_for_job_raises_not_found_without_analysis():
    service = make_service()
    with pytest.raises(NotFoundError):
        service.match_for_job("missing", resume())


def test_match_for_job_refetches_persisted_result_without_recompute():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Built the ordering API with FastAPI"],
            )
        ],
    )
    service._analyses.add("jd-1", analysis(requirement("Experience with FastAPI")))

    first = service.match_for_job("jd-1", candidate)

    # a later analysis change must not leak into the persisted result on re-fetch
    service._analyses.add("jd-1", analysis(requirement("Experience with Django")))
    second = service.match_for_job("jd-1", candidate)

    assert second == first
    assert second.matches[0].status == MatchStatus.STRONG_MATCH


def test_match_for_job_recomputes_when_resume_differs():
    service = make_service()
    candidate = resume(
        skills={"frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Built the ordering API with FastAPI"],
            )
        ],
    )
    service._analyses.add("jd-1", analysis(requirement("Experience with FastAPI")))

    service.match_for_job("jd-1", candidate)
    other = Resume(
        id="resume-2",
        personal_information=PersonalInformation(full_name="Ada Lovelace"),
        skills={"frameworks": ["Django"]},
    )
    recomputed = service.match_for_job("jd-1", other)

    assert recomputed.resume_id == "resume-2"
    assert recomputed.matches[0].status == MatchStatus.TRANSFERABLE