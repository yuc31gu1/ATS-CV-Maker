from datetime import UTC, datetime

from app import catalog
from app.domain.analysis import JobAnalysis, JobRequirement
from app.domain.matching import EvidenceMatch, MatchResult, MatchStatus
from app.domain.resume import Resume
from app.errors import NotFoundError
from app.repositories.base import EntityRepository

_STATUS_RANK = {
    MatchStatus.NO_EVIDENCE: 0,
    MatchStatus.TRANSFERABLE: 1,
    MatchStatus.PARTIAL_MATCH: 2,
    MatchStatus.STRONG_MATCH: 3,
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class MatchingService:
    """Deterministic requirement–evidence matching over the Skill Catalog.

    Statuses are assigned by rules (ADR-0002), never by the LLM:
      - skill in Skills and substantiated in experience/projects → STRONG_MATCH
      - skill in Skills only → PARTIAL_MATCH
      - skill absent but an adjacent (catalog-marked) skill present → TRANSFERABLE
      - otherwise → NO_EVIDENCE
    Adjacent-but-distinct hits (e.g. FastAPI vs Flask) and requirements naming
    multiple distinct skills are surfaced as ambiguous for human review.
    """

    def __init__(
        self,
        *,
        analysis_repository: EntityRepository[JobAnalysis],
        match_repository: EntityRepository[MatchResult],
    ) -> None:
        self._analyses = analysis_repository
        self._matches = match_repository

    def get(self, job_description_id: str) -> MatchResult | None:
        return self._matches.get(job_description_id)

    def match_for_job(self, job_description_id: str, resume: Resume) -> MatchResult:
        """Match a stored Job Analysis against a Master Resume and persist."""
        analysis = self._analyses.get(job_description_id)
        if analysis is None:
            raise NotFoundError(
                "job analysis not found",
                details={"job_description_id": job_description_id},
            )
        result = self.match(analysis, resume)
        result.job_description_id = job_description_id
        result.resume_id = resume.id or ""
        existing = self._matches.get(job_description_id)
        result.created_at = existing.created_at if existing is not None else utcnow()
        return self._matches.add(job_description_id, result)

    def match(self, analysis: JobAnalysis, resume: Resume) -> MatchResult:
        canonical_skills = self._canonical_resume_skills(resume)
        substantiated = self._substantiated_skills(resume)
        matches = [
            self._match_requirement(requirement, canonical_skills, substantiated)
            for requirement in analysis.requirements
        ]
        return MatchResult(
            job_description_id=analysis.job_description_id,
            resume_id=resume.id or "",
            matches=matches,
            created_at=utcnow(),
        )

    @staticmethod
    def _canonical_resume_skills(resume: Resume) -> set[str]:
        return {
            canonical
            for entries in resume.skills.values()
            for name in entries
            if (canonical := catalog.canonical_of(name)) is not None
        }

    @staticmethod
    def _substantiated_skills(
        resume: Resume,
    ) -> dict[str, list[tuple[str, str]]]:
        """Map canonical skill -> [(evidence_id, evidence text)] from the resume."""
        result: dict[str, list[tuple[str, str]]] = {}

        def add(skill: str, evidence_id: str, text: str) -> None:
            entries = result.setdefault(skill, [])
            if (evidence_id, text) not in entries:
                entries.append((evidence_id, text))

        for exp_index, exp in enumerate(resume.experience):
            for bullet_index, bullet in enumerate(exp.bullets):
                for skill in catalog.skills_in_text(bullet):
                    add(skill, f"experience:{exp_index}:bullet:{bullet_index}", bullet)

        for proj_index, proj in enumerate(resume.projects):
            project_label = f"Project: {proj.name}"
            for tech in proj.technologies:
                canonical = catalog.canonical_of(tech)
                if canonical is not None:
                    add(canonical, f"project:{proj_index}", project_label)
            for skill in catalog.skills_in_text(proj.description):
                add(skill, f"project:{proj_index}", project_label)
            for bullet_index, bullet in enumerate(proj.bullets):
                for skill in catalog.skills_in_text(bullet):
                    add(skill, f"project:{proj_index}:bullet:{bullet_index}", bullet)

        for skill, entries in result.items():
            entries.sort(key=lambda item: item[0])
        return result

    def _match_requirement(
        self,
        requirement: JobRequirement,
        canonical_skills: set[str],
        substantiated: dict[str, list[tuple[str, str]]],
    ) -> EvidenceMatch:
        found = catalog.skills_in_text(requirement.requirement)
        if not found:
            return EvidenceMatch(
                requirement=requirement.requirement,
                category=requirement.category,
                importance=requirement.importance,
                status=MatchStatus.NO_EVIDENCE,
                rationale="No catalog skill found in the requirement.",
            )

        candidates = []
        for skill in found:
            if skill in canonical_skills:
                evidence = substantiated.get(skill, [])
                if evidence:
                    candidates.append((MatchStatus.STRONG_MATCH, skill, skill, evidence))
                else:
                    candidates.append((MatchStatus.PARTIAL_MATCH, skill, skill, []))
            else:
                adjacent = sorted(catalog.related_to(skill) & canonical_skills)
                if adjacent:
                    candidates.append((MatchStatus.TRANSFERABLE, skill, adjacent[0], []))
                else:
                    candidates.append((MatchStatus.NO_EVIDENCE, skill, skill, []))

        status, _found, matched_skill, evidence = max(
            candidates, key=lambda c: _STATUS_RANK[c[0]]
        )
        ambiguous = status is MatchStatus.TRANSFERABLE or len(
            {c[1] for c in candidates if _STATUS_RANK[c[0]] > 0}
        ) > 1
        return EvidenceMatch(
            requirement=requirement.requirement,
            category=requirement.category,
            importance=requirement.importance,
            status=status,
            matched_skill=matched_skill,
            ambiguous=ambiguous,
            rationale=self._rationale(status, matched_skill),
            evidence_ids=[item[0] for item in evidence],
            evidence=list(dict.fromkeys(item[1] for item in evidence)),
        )

    @staticmethod
    def _rationale(status: MatchStatus, matched_skill: str | None) -> str:
        if status is MatchStatus.STRONG_MATCH:
            return (
                f"Skill '{matched_skill}' is listed and substantiated by experience "
                "or projects."
            )
        if status is MatchStatus.PARTIAL_MATCH:
            return (
                f"Skill '{matched_skill}' is listed in Skills but not substantiated "
                "by experience or projects."
            )
        if status is MatchStatus.TRANSFERABLE:
            return (
                f"No direct evidence for the required skill; adjacent skill "
                f"'{matched_skill}' is present. Confirm before claiming direct "
                "experience."
            )
        return f"No evidence found for skill '{matched_skill}'."