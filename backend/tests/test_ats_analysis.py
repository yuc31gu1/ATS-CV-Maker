"""AtsAnalysisService: measured keyword/evidence coverage and no fake score.

Covers the T7 acceptance criteria for the ATS Compatibility Analysis: checks
reported as JSON, keyword coverage computed semantically over the Skill
Catalog (synonyms resolve, adjacent skills do not), unsupported requirements
listed explicitly, page count reported honestly, and no pass/fail score.
"""

from datetime import UTC, datetime

import pytest

from app.domain.analysis import (
    Importance,
    JobAnalysis,
    JobRequirement,
    RequirementCategory,
)
from app.domain.ats import ATSAnalysis
from app.domain.matching import EvidenceMatch, MatchResult, MatchStatus
from app.errors import NotFoundError
from app.pdf.validator import PdfValidationReport
from app.repositories.in_memory import InMemoryRepository
from app.services.ats import AtsAnalysisService


def _requirement(
    text: str,
    category: RequirementCategory,
    importance: Importance,
) -> JobRequirement:
    return JobRequirement(
        requirement=text, category=category, importance=importance, context=text
    )


def _analysis() -> JobAnalysis:
    return JobAnalysis(
        id="analysis-1",
        job_description_id="jd-1",
        role="Engineer",
        created_at=datetime.now(UTC),
        requirements=[
            _requirement(
                "Must have PostgreSQL",
                RequirementCategory.REQUIRED,
                Importance.HIGH,
            ),
            _requirement(
                "Experience with FastAPI",
                RequirementCategory.REQUIRED,
                Importance.MEDIUM,
            ),
            _requirement(
                "Nice to have Redis",
                RequirementCategory.PREFERRED,
                Importance.LOW,
            ),
            _requirement(
                "Excellent communication skills",
                RequirementCategory.SOFT_SKILL,
                Importance.MEDIUM,
            ),
        ],
    )


def _match() -> MatchResult:
    return MatchResult(
        job_description_id="jd-1",
        resume_id="r-1",
        created_at=datetime.now(UTC),
        matches=[
            EvidenceMatch(
                requirement="Must have PostgreSQL",
                category=RequirementCategory.REQUIRED,
                importance=Importance.HIGH,
                status=MatchStatus.STRONG_MATCH,
                matched_skill="postgresql",
            ),
            EvidenceMatch(
                requirement="Experience with FastAPI",
                category=RequirementCategory.REQUIRED,
                importance=Importance.MEDIUM,
                status=MatchStatus.PARTIAL_MATCH,
                matched_skill="fastapi",
            ),
            EvidenceMatch(
                requirement="Nice to have Redis",
                category=RequirementCategory.PREFERRED,
                importance=Importance.LOW,
                status=MatchStatus.NO_EVIDENCE,
            ),
            EvidenceMatch(
                requirement="Excellent communication skills",
                category=RequirementCategory.SOFT_SKILL,
                importance=Importance.MEDIUM,
                status=MatchStatus.NO_EVIDENCE,
            ),
        ],
    )


def _report(text: str = "") -> PdfValidationReport:
    return PdfValidationReport(
        extracted_text=text,
        page_count=1,
        single_column=True,
        standard_headings=True,
        critical_info_in_body=True,
        unexpected_tables=0,
        unexpected_graphics=0,
    )


def _service(
    analysis: JobAnalysis, match: MatchResult
) -> AtsAnalysisService:
    analysis_repo = InMemoryRepository()
    match_repo = InMemoryRepository()
    analysis_repo.add(analysis.job_description_id, analysis)
    match_repo.add(match.job_description_id, match)
    return AtsAnalysisService(
        analysis_repository=analysis_repo, match_repository=match_repo
    )


def test_required_coverage_is_computed_semantically_over_the_catalog() -> None:
    # "Postgres" is an alias for canonical "postgresql"; the requirement says
    # "PostgreSQL", so the JD requirement is covered even though the PDF text
    # uses the shorter surface form. Synonym resolution happens in the catalog.
    report = _report(
        "Ada Lovelace Backend Engineer who builds with FastAPI and Postgres."
    )
    analysis = _analysis()

    result = _service(analysis, _match()).analyze("jd-1", report)

    assert result.required_keyword_coverage == 1.0


def test_adjacent_skills_never_count_as_keyword_coverage() -> None:
    # "Django" is related to "FastAPI", never a synonym (ADR-0002): a PDF that
    # mentions only Django does not cover the FastAPI requirement.
    report = _report("Built with Django and Postgres.")
    analysis = _analysis()

    result = _service(analysis, _match()).analyze("jd-1", report)

    assert result.required_keyword_coverage == 0.5


def test_preferred_coverage_spans_all_preferred_terms() -> None:
    analysis = _analysis()
    report = _report("Redis is used for caching.")

    result = _service(analysis, _match()).analyze("jd-1", report)

    assert result.preferred_keyword_coverage == 1.0


def test_evidence_coverage_counts_strong_and_partial_over_important() -> None:
    result = _service(_analysis(), _match()).analyze(
        "jd-1", _report("anything")
    )

    # 3 important requirements (2x REQUIRED, 1x SOFT_SKILL); PostgreSQL and
    # FastAPI carry evidence; the soft-skill requirement has none.
    assert result.evidence_coverage == 2 / 3


def test_unsupported_requirements_are_listed_explicitly() -> None:
    result = _service(_analysis(), _match()).analyze(
        "jd-1", _report("")
    )

    assert result.unsupported_requirements == ["Excellent communication skills"]


def test_no_supported_requirements_means_unknown_coverage_not_zero() -> None:
    analysis = JobAnalysis(
        id="a2",
        job_description_id="jd-2",
        role="Analyst",
        created_at=datetime.now(UTC),
        requirements=[
            _requirement(
                "Strong analytical thinking",
                RequirementCategory.REQUIRED,
                Importance.HIGH,
            )
        ],
    )
    match = MatchResult(
        job_description_id="jd-2",
        resume_id="r-2",
        created_at=datetime.now(UTC),
        matches=[],
    )

    result = _service(analysis, match).analyze("jd-2", _report(""))

    assert result.required_keyword_coverage is None
    assert result.unsupported_requirements == ["Strong analytical thinking"]


def test_analysis_reports_measured_checks_and_never_a_fake_score() -> None:
    result = _service(_analysis(), _match()).analyze(
        "jd-1", _report("Ada Lovelace Redis")
    )

    assert result.pdf_text_extraction is True
    assert result.single_column is True
    assert result.standard_headings is True
    assert result.critical_info_in_body is True
    assert result.unexpected_tables == 0
    assert result.unexpected_graphics == 0
    assert result.page_count == 1
    assert "ats_score" not in ATSAnalysis.model_fields
    assert "ats_rating" not in ATSAnalysis.model_fields


def test_warnings_surface_unsupported_no_evidence_and_tables() -> None:
    report = _report("Ada Lovelace Redis").model_copy(
        update={"unexpected_tables": 2}
    )
    result = _service(_analysis(), _match()).analyze("jd-1", report)

    messages = "\n".join(result.warnings)
    assert "could not be measured against the Skill Catalog" in messages
    assert "No evidence found for 1 important requirements" in messages
    assert "table-separated" in messages


def test_warnings_surface_ambiguous_matches() -> None:
    analysis = _analysis()
    match = _match()
    match.matches[1] = match.matches[1].model_copy(
        update={"status": MatchStatus.TRANSFERABLE, "ambiguous": True}
    )
    result = _service(analysis, match).analyze("jd-1", _report(""))

    assert any("adjacent skills" in warning for warning in result.warnings)


def test_missing_analysis_returns_not_found() -> None:
    service = AtsAnalysisService(
        analysis_repository=InMemoryRepository(),
        match_repository=InMemoryRepository(),
    )
    with pytest.raises(NotFoundError):
        service.analyze("jd-missing", _report(""))


def test_missing_match_result_returns_not_found() -> None:
    analysis_repo = InMemoryRepository()
    analysis_repo.add("jd-1", _analysis())
    service = AtsAnalysisService(
        analysis_repository=analysis_repo,
        match_repository=InMemoryRepository(),
    )
    with pytest.raises(NotFoundError):
        service.analyze("jd-1", _report(""))