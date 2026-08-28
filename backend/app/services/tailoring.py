import json
import re
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app import catalog
from app.domain.analysis import Importance, JobAnalysis
from app.domain.matching import MatchResult, MatchStatus
from app.domain.resume import Resume
from app.domain.tailoring import (
    ChangeAction,
    ChangeStatus,
    LLMTailoredOutput,
    ReviewDecision,
    RewrittenBullet,
    SelectedBullet,
    SelectedProject,
    TailorChangeKind,
    TailoredChange,
    TailoredResume,
    TailoringScope,
)
from app.domain.versioning import ResumeVersion
from app.errors import (
    LLMValidationFailed,
    NotFoundError,
    ResourceValidationError,
    TailoringFailed,
)
from app.llm.base import (
    TAILOR_SCOPE_END_MARKER,
    TAILOR_SCOPE_START_MARKER,
    LLMProvider,
)
from app.repositories.base import EntityRepository
from app.repositories.resume import ResumeRepository
from app.services.verification import ClaimVerification
from app.time import utcnow

MAX_RETRIES = 1

_IMPORTANCE_RANK = {Importance.HIGH: 3, Importance.MEDIUM: 2, Importance.LOW: 1}
_STATUS_RANK = {
    MatchStatus.NO_EVIDENCE: 0,
    MatchStatus.TRANSFERABLE: 1,
    MatchStatus.PARTIAL_MATCH: 2,
    MatchStatus.STRONG_MATCH: 3,
}


class TailoringEngine:
    """Deterministic selection and ordering of evidence (ADR-0001).

    Decides which evidence survives into the Tailored Resume, its order,
    which projects surface, and the skills ordering. The engine never invents
    evidence and never assigns match statuses (ADR-0002).
    """

    def scope(self, result: MatchResult, resume: Resume) -> TailoringScope:
        matched_skills = {
            m.matched_skill
            for m in result.matches
            if m.matched_skill is not None
            and m.status in (MatchStatus.STRONG_MATCH, MatchStatus.PARTIAL_MATCH)
        }
        bullets = self._select_bullets(resume, result.matches, matched_skills)
        projects = self._select_projects(resume, result.matches, matched_skills)
        return TailoringScope(
            summary=resume.summary,
            bullets=bullets,
            projects=projects,
            skills=self._order_skills(resume.skills, matched_skills, result.matches),
        )

    def _select_bullets(
        self,
        resume: Resume,
        matches: list,
        matched_skills: set[str],
    ) -> list[SelectedBullet]:
        selected: list[SelectedBullet] = []
        for exp_index, exp in enumerate(resume.experience):
            for bullet_index, bullet in enumerate(exp.bullets):
                evidence_id = f"experience:{exp_index}:bullet:{bullet_index}"
                matched = self._matched_for_text(bullet, matches, matched_skills)
                if not matched:
                    continue
                selected.append(
                    SelectedBullet(
                        evidence_id=evidence_id,
                        original=bullet,
                        matched_requirements=[m.requirement for m in matched],
                        score=self._score(matched),
                    )
                )
        for proj_index, proj in enumerate(resume.projects):
            for bullet_index, bullet in enumerate(proj.bullets):
                evidence_id = f"project:{proj_index}:bullet:{bullet_index}"
                matched = self._matched_for_text(bullet, matches, matched_skills)
                if not matched:
                    continue
                selected.append(
                    SelectedBullet(
                        evidence_id=evidence_id,
                        original=bullet,
                        matched_requirements=[m.requirement for m in matched],
                        score=self._score(matched),
                    )
                )
        selected.sort(key=lambda b: (-b.score, b.evidence_id))
        return selected

    @staticmethod
    def _matched_for_text(
        text: str,
        matches: list,
        matched_skills: set[str],
    ) -> list:
        hit_skills = set(catalog.skills_in_text(text)) & matched_skills
        if not hit_skills:
            return []
        return [m for m in matches if m.matched_skill in hit_skills]

    @staticmethod
    def _score(matched: list) -> int:
        return max(
            _IMPORTANCE_RANK[m.importance] * 10 + _STATUS_RANK[m.status]
            for m in matched
        )

    def _select_projects(
        self,
        resume: Resume,
        matches: list,
        matched_skills: set[str],
    ) -> list[SelectedProject]:
        selected: list[SelectedProject] = []
        for index, proj in enumerate(resume.projects):
            proj_skills = {
                canonical
                for tech in proj.technologies
                if (canonical := catalog.canonical_of(tech)) is not None
            }
            for text in (proj.name, proj.description, *proj.bullets):
                proj_skills.update(catalog.skills_in_text(text))
            hit = proj_skills & matched_skills
            if not hit:
                continue
            matched = [m for m in matches if m.matched_skill in hit]
            selected.append(
                SelectedProject(
                    index=index,
                    name=proj.name,
                    matched_requirements=[m.requirement for m in matched],
                )
            )
        selected.sort(key=lambda p: p.index)
        return selected

    def _order_skills(
        self,
        skills: dict[str, list[str]],
        matched_skills: set[str],
        matches: list,
    ) -> dict[str, list[str]]:
        importance_of: dict[str, int] = {}
        for match in matches:
            if match.matched_skill is not None and match.matched_skill in matched_skills:
                importance_of[match.matched_skill] = max(
                    importance_of.get(match.matched_skill, 0),
                    _IMPORTANCE_RANK[match.importance],
                )
        ordered: dict[str, list[str]] = {}
        for category, names in skills.items():
            ordered[category] = sorted(
                names,
                key=lambda name: self._skill_sort_key(
                    name, matched_skills, importance_of
                ),
            )
        return ordered

    @staticmethod
    def _skill_sort_key(
        name: str,
        matched_skills: set[str],
        importance_of: dict[str, int],
    ) -> tuple[int, int, str]:
        canonical = catalog.canonical_of(name)
        if canonical in matched_skills:
            return (0, -importance_of.get(canonical, 0), name.lower())
        return (1, 0, name.lower())


class TailoringService:
    """Orchestrates tailoring: snapshot -> engine scope -> LLM rewrite -> verify.

    The Master Resume is never mutated: an immutable ResumeVersion snapshot is
    captured when the job starts, and every Tailored Resume pins to it. Bad
    LLM output fails cleanly with LLM_VALIDATION_FAILED; untraceable claims
    fail with TAILORING_FAILED.
    """

    def __init__(
        self,
        *,
        version_repository: EntityRepository[ResumeVersion],
        tailored_repository: EntityRepository[TailoredResume],
        resume_repository: ResumeRepository,
        analysis_repository: EntityRepository[JobAnalysis],
        match_repository: EntityRepository[MatchResult],
        llm_provider: LLMProvider,
        engine: TailoringEngine | None = None,
        verification: ClaimVerification | None = None,
    ) -> None:
        self._versions = version_repository
        self._tailored = tailored_repository
        self._resumes = resume_repository
        self._analyses = analysis_repository
        self._matches = match_repository
        self._llm = llm_provider
        self._engine = engine or TailoringEngine()
        self._verification = verification or ClaimVerification()

    def get(self, job_description_id: str) -> TailoredResume | None:
        return self._tailored.get(job_description_id)

    def run(self, payload: dict) -> dict:
        """TAILOR job body: full tailoring or a single-change regeneration."""
        job_description_id = payload["job_description_id"]
        if payload.get("action") == "regenerate":
            result = self.regenerate_change(job_description_id, payload["change_key"])
        else:
            result = self.tailor(job_description_id, payload["resume_id"])
        return result.model_dump(mode="json")

    def tailor(self, job_description_id: str, resume_id: str) -> TailoredResume:
        resume = self._resumes.get(resume_id)
        if resume is None:
            raise NotFoundError("resume not found", details={"id": resume_id})
        if self._matches.get(job_description_id) is None:
            raise NotFoundError(
                "match result not found",
                details={"job_description_id": job_description_id},
            )
        version = self._capture_snapshot(resume)
        scope = self._engine.scope(self._matches.get(job_description_id), version.data)
        output = self._rewrite(scope, job_description_id)
        return self._build_tailored(
            job_description_id, resume_id, version, scope, output
        )

    def _capture_snapshot(self, resume: Resume) -> ResumeVersion:
        version = ResumeVersion(
            id=str(uuid4()),
            resume_id=resume.id or "",
            data=resume.model_copy(deep=True),
            created_at=utcnow(),
        )
        return self._versions.add(version.id, version)

    def _rewrite(self, scope: TailoringScope, job_description_id: str) -> LLMTailoredOutput:
        prompt = self._build_prompt(scope, job_description_id)
        last_error: ValidationError | None = None
        for _attempt in range(MAX_RETRIES + 1):
            raw = self._llm.generate_structured(
                prompt=prompt, output_schema=LLMTailoredOutput
            )
            try:
                return self._coerce(raw, LLMTailoredOutput)
            except ValidationError as exc:
                last_error = exc
                prompt = self._build_prompt(scope, job_description_id, retry_error=exc)
        raise LLMValidationFailed(
            "LLM returned structured output that failed validation",
            details={"validation_error": str(last_error)},
        )

    def _build_prompt(
        self,
        scope: TailoringScope,
        job_description_id: str,
        *,
        retry_error: ValidationError | None = None,
    ) -> str:
        role = self._role_for(job_description_id)
        schema_json = json.dumps(LLMTailoredOutput.model_json_schema())
        scope_json = json.dumps(scope.model_dump(mode="json"))
        prompt = (
            f"Rewrite the resume content for the role {role!r}, ONLY within the "
            "scope below. Every rewrite must keep technologies, numbers, "
            "employers, and titles traceable to the source text: never invent "
            "technologies or metrics.\n"
            f"{TAILOR_SCOPE_START_MARKER}\n{scope_json}\n{TAILOR_SCOPE_END_MARKER}\n"
            "Return a single JSON object matching this schema exactly:\n"
            f"{schema_json}\n"
            "Each bullet's source_evidence_ids must be the evidence id it rewrites."
        )
        if retry_error is not None:
            prompt += (
                "\nYour previous response failed validation and must not be "
                f"repeated. Return valid JSON matching the schema. Error: {retry_error}"
            )
        return prompt

    def _role_for(self, job_description_id: str) -> str:
        analysis = self._analyses.get(job_description_id)
        return analysis.role if analysis is not None else "the target role"

    @staticmethod
    def _coerce(raw, schema: type[BaseModel]) -> BaseModel:
        if isinstance(raw, schema):
            return raw
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        return schema.model_validate(raw)

    def _build_tailored(
        self,
        job_description_id: str,
        resume_id: str,
        version: ResumeVersion,
        scope: TailoringScope,
        output: LLMTailoredOutput,
    ) -> TailoredResume:
        snapshot = version.data
        changes, summary, experience, projects = self._apply_rewrites(
            snapshot, scope, output
        )
        tailored = TailoredResume(
            job_description_id=job_description_id,
            resume_version_id=version.id,
            resume_id=resume_id,
            personal_information=snapshot.personal_information,
            summary=summary,
            skills=scope.skills,
            experience=experience,
            education=snapshot.education,
            projects=projects,
            certifications=snapshot.certifications,
            changes=changes,
            created_at=utcnow(),
        )
        self._verify(tailored.changes, snapshot)
        return self._tailored.add(job_description_id, tailored)

    def _apply_rewrites(
        self,
        snapshot: Resume,
        scope: TailoringScope,
        output: LLMTailoredOutput,
    ) -> tuple[list[TailoredChange], str, list, list]:
        scope_by_id = {b.evidence_id: b for b in scope.bullets}
        llm_by_id = {b.evidence_id: b for b in output.bullets if b.evidence_id in scope_by_id}
        changes: list[TailoredChange] = []

        if scope.summary:
            tailored_summary = output.summary if output.summary is not None else scope.summary
            changes.append(
                TailoredChange(
                    key="summary",
                    kind=TailorChangeKind.SUMMARY,
                    section="summary",
                    original=scope.summary,
                    tailored=tailored_summary,
                    reason=output.summary_reason or "Rewritten for the target role.",
                    source_evidence_ids=(
                        output.summary_source_evidence_ids
                        or [b.evidence_id for b in scope.bullets]
                    ),
                )
            )
        else:
            tailored_summary = snapshot.summary

        experience = []
        for exp_index, exp in enumerate(snapshot.experience):
            new_bullets = []
            for bullet_index, original in enumerate(exp.bullets):
                evidence_id = f"experience:{exp_index}:bullet:{bullet_index}"
                if evidence_id not in scope_by_id:
                    continue
                rewritten = llm_by_id.get(evidence_id)
                new_bullets.append(
                    self._bullet_change(
                        changes,
                        evidence_id,
                        "experience",
                        original,
                        rewritten,
                    )
                )
            if new_bullets:
                experience.append(exp.model_copy(update={"bullets": new_bullets}))

        selected_indices = {p.index for p in scope.projects}
        projects = []
        for index, proj in enumerate(snapshot.projects):
            if index not in selected_indices:
                continue
            new_bullets = []
            for bullet_index, original in enumerate(proj.bullets):
                evidence_id = f"project:{index}:bullet:{bullet_index}"
                if evidence_id not in scope_by_id:
                    new_bullets.append(original)
                    continue
                rewritten = llm_by_id.get(evidence_id)
                new_bullets.append(
                    self._bullet_change(
                        changes,
                        evidence_id,
                        "project",
                        original,
                        rewritten,
                    )
                )
            projects.append(proj.model_copy(update={"bullets": new_bullets}))

        return changes, tailored_summary, experience, projects

    @staticmethod
    def _bullet_change(
        changes: list[TailoredChange],
        evidence_id: str,
        section: str,
        original: str,
        rewritten: RewrittenBullet | None,
    ) -> str:
        if rewritten is not None:
            tailored = rewritten.text
            reason = rewritten.reason
            source_ids = rewritten.source_evidence_ids or [evidence_id]
        else:
            tailored = original
            reason = "No rewrite produced; kept as engine-selected evidence."
            source_ids = [evidence_id]
        changes.append(
            TailoredChange(
                key=evidence_id,
                kind=TailorChangeKind.BULLET,
                section=section,
                original=original,
                tailored=tailored,
                reason=reason,
                source_evidence_ids=source_ids,
            )
        )
        return tailored

    def _verify(self, changes: list[TailoredChange], snapshot: Resume) -> None:
        reasons = [
            reason
            for change in changes
            for reason in self._verification.verify(
                change=change, snapshot=snapshot
            ).reasons
        ]
        if reasons:
            raise TailoringFailed(
                "tailored resume contains untraceable claims",
                details={"reasons": reasons},
            )

    def apply_decisions(
        self, job_description_id: str, decisions: list[ReviewDecision]
    ) -> TailoredResume:
        tailored = self.get(job_description_id)
        if tailored is None:
            raise NotFoundError(
                "tailored resume not found",
                details={"job_description_id": job_description_id},
            )
        change_by_key = {change.key: change for change in tailored.changes}
        for decision in decisions:
            change = change_by_key.get(decision.key)
            if change is None:
                raise ResourceValidationError(
                    "unknown change key", details={"key": decision.key}
                )
            if decision.action is ChangeAction.accept:
                change.status = ChangeStatus.ACCEPTED
                self._set_content(tailored, change.key, change.tailored)
            elif decision.action is ChangeAction.reject:
                change.status = ChangeStatus.REJECTED
                self._set_content(tailored, change.key, change.original)
            elif decision.action is ChangeAction.edit:
                if not decision.text:
                    raise ResourceValidationError(
                        "edited text is required", details={"key": decision.key}
                    )
                change.status = ChangeStatus.EDITED
                change.edited_text = decision.text
                self._set_content(tailored, change.key, decision.text)
        return self._tailored.add(job_description_id, tailored)

    @staticmethod
    def _set_content(tailored: TailoredResume, key: str, text: str) -> None:
        if key == "summary":
            tailored.summary = text
            return
        match = re.fullmatch(r"(experience|project):(\d+):bullet:(\d+)", key)
        if match is None:
            raise ResourceValidationError(
                "unknown change key", details={"key": key}
            )
        section, index, bullet_index = match.group(1), int(match.group(2)), int(
            match.group(3)
        )
        if section == "experience":
            tailored.experience[index].bullets[bullet_index] = text
        else:
            tailored.projects[index].bullets[bullet_index] = text

    def regenerate_change(
        self, job_description_id: str, change_key: str
    ) -> TailoredResume:
        tailored = self.get(job_description_id)
        if tailored is None:
            raise NotFoundError(
                "tailored resume not found",
                details={"job_description_id": job_description_id},
            )
        version = self._versions.get(tailored.resume_version_id)
        if version is None:
            raise NotFoundError(
                "resume version not found",
                details={"id": tailored.resume_version_id},
            )
        target = next(
            (change for change in tailored.changes if change.key == change_key), None
        )
        if target is None:
            raise NotFoundError("change not found", details={"key": change_key})

        scope = self._scope_for_change(job_description_id, version.data, change_key)
        output = self._rewrite(scope, job_description_id)

        if change_key == "summary":
            new_text = output.summary if output.summary is not None else scope.summary
            new_reason = output.summary_reason or "Rewritten for the target role."
            new_source_ids = output.summary_source_evidence_ids or [
                b.evidence_id for b in scope.bullets
            ]
        else:
            rewritten = next(
                (b for b in output.bullets if b.evidence_id == change_key), None
            )
            if rewritten is None:
                new_text = target.original
                new_reason = "No rewrite produced; kept as engine-selected evidence."
                new_source_ids = [change_key]
            else:
                new_text = rewritten.text
                new_reason = rewritten.reason
                new_source_ids = rewritten.source_evidence_ids or [change_key]

        regenerated = TailoredChange(
            key=target.key,
            kind=target.kind,
            section=target.section,
            original=target.original,
            tailored=new_text,
            reason=new_reason,
            source_evidence_ids=new_source_ids,
        )
        result = self._verification.verify(change=regenerated, snapshot=version.data)
        if not result.passed:
            raise TailoringFailed(
                "regenerated change contains untraceable claims",
                details={"reasons": result.reasons},
            )

        for index, change in enumerate(tailored.changes):
            if change.key == change_key:
                tailored.changes[index] = regenerated
                break
        self._set_content(tailored, change_key, new_text)
        return self._tailored.add(job_description_id, tailored)

    def _scope_for_change(
        self, job_description_id: str, snapshot: Resume, change_key: str
    ) -> TailoringScope:
        match_result = self._matches.get(job_description_id)
        if match_result is None:
            raise NotFoundError(
                "match result not found",
                details={"job_description_id": job_description_id},
            )
        scope = self._engine.scope(match_result, snapshot)
        if change_key == "summary":
            return scope
        bullet = next(
            (b for b in scope.bullets if b.evidence_id == change_key), None
        )
        if bullet is None:
            raise NotFoundError("change not in scope", details={"key": change_key})
        return TailoringScope(
            summary="",
            bullets=[bullet],
            projects=[],
            skills=scope.skills,
        )