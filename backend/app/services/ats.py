"""ATS Compatibility Analysis for a generated PDF (user stories 26-27).

Keyword coverage is computed semantically over the curated Skill Catalog
(ADR-0002): a high-priority requirement is covered when at least one of the
catalog skills it resolves to appears in the extracted PDF text, matched on
canonical or alias surface forms. Requirements the catalog cannot measure are
listed explicitly as unsupported — never folded into a fake percentage. The
report carries only measured checks; there is no pass/fail "ATS score".
"""

from app import catalog
from app.domain.analysis import Importance, JobAnalysis, JobRequirement, RequirementCategory
from app.domain.ats import ATSAnalysis
from app.domain.matching import MatchResult, MatchStatus
from app.errors import NotFoundError
from app.pdf.validator import PdfValidationReport
from app.repositories.base import EntityRepository

_HIGH_PRIORITY = {Importance.HIGH, Importance.MEDIUM}


class AtsAnalysisService:
    """Computes the measured ATS Compatibility Analysis for one generated PDF."""

    def __init__(
        self,
        *,
        analysis_repository: EntityRepository[JobAnalysis],
        match_repository: EntityRepository[MatchResult],
    ) -> None:
        self._analyses = analysis_repository
        self._matches = match_repository

    def analyze(
        self,
        job_description_id: str,
        report: PdfValidationReport,
    ) -> ATSAnalysis:
        analysis = self._analyses.get(job_description_id)
        if analysis is None:
            raise NotFoundError(
                "job analysis not found",
                details={"job_description_id": job_description_id},
            )
        match_result = self._matches.get(job_description_id)
        if match_result is None:
            raise NotFoundError(
                "match result not found",
                details={"job_description_id": job_description_id},
            )
        return self.compute(analysis, match_result, report)

    @staticmethod
    def compute(
        analysis: JobAnalysis,
        match_result: MatchResult,
        report: PdfValidationReport,
    ) -> ATSAnalysis:
        text = report.extracted_text
        status_by_requirement = {
            match.requirement: match.status for match in match_result.matches
        }
        unsupported = [
            requirement.requirement
            for requirement in analysis.requirements
            if not catalog.skills_in_text(requirement.requirement)
        ]
        warnings = AtsAnalysisService._warnings(
            match_result, unsupported, report
        )
        return ATSAnalysis(
            required_keyword_coverage=AtsAnalysisService._coverage(
                AtsAnalysisService._supported(
                    analysis, RequirementCategory.REQUIRED
                ),
                text,
            ),
            preferred_keyword_coverage=AtsAnalysisService._coverage(
                AtsAnalysisService._supported(
                    analysis, RequirementCategory.PREFERRED
                ),
                text,
            ),
            evidence_coverage=AtsAnalysisService._evidence_coverage(
                analysis, status_by_requirement
            ),
            pdf_text_extraction=True,
            single_column=report.single_column,
            standard_headings=report.standard_headings,
            critical_info_in_body=report.critical_info_in_body,
            unexpected_tables=report.unexpected_tables,
            unexpected_graphics=report.unexpected_graphics,
            page_count=report.page_count,
            warnings=warnings,
            unsupported_requirements=sorted(unsupported),
        )

    @staticmethod
    def _supported(
        analysis: JobAnalysis, category: RequirementCategory
    ) -> list[JobRequirement]:
        return [
            requirement
            for requirement in analysis.requirements
            if (
                requirement.category is category
                and (
                    category is not RequirementCategory.REQUIRED
                    or requirement.importance in _HIGH_PRIORITY
                )
                and catalog.skills_in_text(requirement.requirement)
            )
        ]

    @staticmethod
    def _coverage(
        requirements: list[JobRequirement], text: str
    ) -> float | None:
        if not requirements:
            return None
        pdf_skills = set(catalog.skills_in_text(text))
        covered = sum(
            1
            for requirement in requirements
            if set(catalog.skills_in_text(requirement.requirement)) & pdf_skills
        )
        return covered / len(requirements)

    @staticmethod
    def _evidence_coverage(
        analysis: JobAnalysis,
        status_by_requirement: dict[str, MatchStatus],
    ) -> float | None:
        important = [
            requirement
            for requirement in analysis.requirements
            if requirement.importance in _HIGH_PRIORITY
        ]
        if not important:
            return None
        covered = sum(
            1
            for requirement in important
            if status_by_requirement.get(requirement.requirement)
            in (MatchStatus.STRONG_MATCH, MatchStatus.PARTIAL_MATCH)
        )
        return covered / len(important)

    @staticmethod
    def _warnings(
        match_result: MatchResult,
        unsupported: list[str],
        report: PdfValidationReport,
    ) -> list[str]:
        warnings: list[str] = []
        if unsupported:
            warnings.append(
                f"{len(unsupported)} requirements could not be measured against "
                "the Skill Catalog and are listed as unsupported."
            )
        no_evidence = [
            match.requirement
            for match in match_result.matches
            if match.importance in _HIGH_PRIORITY
            and match.status is MatchStatus.NO_EVIDENCE
        ]
        if no_evidence:
            warnings.append(
                f"No evidence found for {len(no_evidence)} important "
                f"requirements: {'; '.join(no_evidence)}."
            )
        ambiguous = [match for match in match_result.matches if match.ambiguous]
        if ambiguous:
            warnings.append(
                f"{len(ambiguous)} requirements matched adjacent skills and "
                "should be reviewed before claiming direct experience."
            )
        if report.unexpected_tables:
            warnings.append(
                f"The PDF contains {report.unexpected_tables} table-separated "
                "regions, which ATS parsers may misread."
            )
        if report.unexpected_graphics:
            warnings.append(
                f"The PDF embeds {report.unexpected_graphics} graphic(s), "
                "which ATS parsers may ignore."
            )
        return warnings