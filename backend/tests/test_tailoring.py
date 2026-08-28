from datetime import UTC, datetime

import pytest

from app.domain.analysis import (
    Importance,
    JobAnalysis,
    JobRequirement,
    RequirementCategory,
)
from app.domain.matching import EvidenceMatch, MatchResult, MatchStatus
from app.domain.resume import (
    Experience,
    PersonalInformation,
    Project,
    Resume,
)
from app.domain.tailoring import (
    ChangeAction,
    ChangeStatus,
    LLMTailoredOutput,
    ReviewDecision,
    RewrittenBullet,
    TailorChangeKind,
    TailoredChange,
    TailoredResume,
)
from app.errors import LLMValidationFailed, NotFoundError, TailoringFailed
from app.llm.fixture import FixtureLLMProvider
from app.repositories.in_memory import InMemoryRepository
from app.repositories.resume import InMemoryResumeRepository
from app.services.tailoring import TailoringEngine, TailoringService
from app.services.verification import ClaimVerification

now = datetime.now(UTC)


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
        created_at=now,
    )


def strong_match(requirement: JobRequirement, skill: str, evidence_ids: list[str]) -> EvidenceMatch:
    return EvidenceMatch(
        requirement=requirement.requirement,
        category=requirement.category,
        importance=requirement.importance,
        status=MatchStatus.STRONG_MATCH,
        matched_skill=skill,
        evidence_ids=evidence_ids,
        evidence=["evidence"],
    )


def partial_match(requirement: JobRequirement, skill: str) -> EvidenceMatch:
    return EvidenceMatch(
        requirement=requirement.requirement,
        category=requirement.category,
        importance=requirement.importance,
        status=MatchStatus.PARTIAL_MATCH,
        matched_skill=skill,
    )


def resume(**kwargs) -> Resume:
    defaults = {
        "personal_information": PersonalInformation(full_name="Ada Lovelace"),
        "summary": "Backend engineer who builds API platforms.",
        "skills": {"frameworks": ["FastAPI"]},
        "experience": [
            Experience(
                company="Acme",
                title="Engineer",
                start_date="2021-03",
                bullets=["Built the ordering API with FastAPI", "Wrote UI copy"],
            )
        ],
    }
    defaults.update(kwargs)
    return Resume(id="resume-1", **defaults)


def make_service(
    provider: FixtureLLMProvider | None = None,
    resume_override: Resume | None = None,
) -> TailoringService:
    versions = InMemoryRepository()
    tailored = InMemoryRepository()
    analyses = InMemoryRepository()
    matches = InMemoryRepository()
    analyses.add("jd-1", analysis(requirement("Experience with FastAPI")))
    matches.add(
        "jd-1",
        MatchResult(
            job_description_id="jd-1",
            resume_id="resume-1",
            matches=[strong_match(requirement("Experience with FastAPI"), "fastapi", ["experience:0:bullet:0"])],
            created_at=now,
        ),
    )
    resume_repo = InMemoryResumeRepository()
    resume_repo.create(resume_override or resume())
    return TailoringService(
        version_repository=versions,
        tailored_repository=tailored,
        resume_repository=resume_repo,
        analysis_repository=analyses,
        match_repository=matches,
        llm_provider=provider or FixtureLLMProvider(),
    )


class TestTailoringEngine:
    def test_selects_only_evidence_substantiating_matched_requirements(self):
        engine = TailoringEngine()
        candidate = resume(
            skills={"frameworks": ["FastAPI"]},
            experience=[
                Experience(
                    company="Acme",
                    title="Engineer",
                    start_date="2021-03",
                    bullets=["Built the ordering API with FastAPI", "Wrote UI copy"],
                ),
                Experience(
                    company="Beta",
                    title="Designer",
                    start_date="2019-01",
                    bullets=["Designed the marketing site"],
                ),
            ],
        )
        result = MatchResult(
            job_description_id="jd-1",
            resume_id="resume-1",
            matches=[strong_match(requirement("Experience with FastAPI"), "fastapi", ["experience:0:bullet:0"])],
            created_at=now,
        )

        scope = engine.scope(result, candidate)

        assert [b.evidence_id for b in scope.bullets] == ["experience:0:bullet:0"]
        assert "Wrote UI copy" not in [b.original for b in scope.bullets]
        assert scope.bullets[0].matched_requirements == ["Experience with FastAPI"]
        assert scope.bullets[0].score > 0

    def test_orders_bullets_by_importance_then_strength(self):
        engine = TailoringEngine()
        candidate = resume(
            skills={"frameworks": ["FastAPI"], "tools": ["Postgres"]},
            experience=[
                Experience(
                    company="Acme",
                    title="Engineer",
                    start_date="2021-03",
                    bullets=[
                        "Used Postgres for migrations",
                        "Built the ordering API with FastAPI",
                    ],
                )
            ],
        )
        matches = [
            strong_match(
                requirement("Experience with PostgreSQL", importance=Importance.MEDIUM),
                "postgresql",
                ["experience:0:bullet:0"],
            ),
            strong_match(
                requirement("Experience with FastAPI", importance=Importance.HIGH),
                "fastapi",
                ["experience:0:bullet:1"],
            ),
        ]
        result = MatchResult(job_description_id="jd-1", resume_id="resume-1", matches=matches, created_at=now)

        scope = engine.scope(result, candidate)

        # HIGH-importance FastAPI bullet ranks above MEDIUM Postgres bullet
        assert scope.bullets[0].evidence_id == "experience:0:bullet:1"
        assert scope.bullets[1].evidence_id == "experience:0:bullet:0"

    def test_surfaces_matched_projects_and_drops_unmatched(self):
        engine = TailoringEngine()
        candidate = resume(
            skills={"frameworks": ["FastAPI"]},
            projects=[
                Project(name="Ordering service", technologies=["FastAPI"], bullets=["Built with FastAPI"]),
                Project(name="Design system", technologies=["Figma"]),
            ],
        )
        result = MatchResult(
            job_description_id="jd-1",
            resume_id="resume-1",
            matches=[strong_match(requirement("Experience with FastAPI"), "fastapi", ["project:0"])],
            created_at=now,
        )

        scope = engine.scope(result, candidate)

        assert [p.name for p in scope.projects] == ["Ordering service"]

    def test_orders_skills_matched_first(self):
        engine = TailoringEngine()
        candidate = resume(
            skills={
                "frameworks": ["Flask", "FastAPI"],
                "tools": ["Docker", "Git"],
            }
        )
        result = MatchResult(
            job_description_id="jd-1",
            resume_id="resume-1",
            matches=[strong_match(requirement("Experience with FastAPI"), "fastapi", ["experience:0:bullet:0"])],
            created_at=now,
        )

        scope = engine.scope(result, candidate)

        assert scope.skills["frameworks"] == ["FastAPI", "Flask"]
        assert scope.skills["tools"] == ["Docker", "Git"]

    def test_is_deterministic(self):
        engine = TailoringEngine()
        candidate = resume(
            skills={"frameworks": ["FastAPI"], "tools": ["Postgres"]},
            experience=[
                Experience(
                    company="Acme",
                    title="Engineer",
                    start_date="2021-03",
                    bullets=["Used Postgres for migrations", "Built the ordering API with FastAPI"],
                )
            ],
        )
        result = MatchResult(
            job_description_id="jd-1",
            resume_id="resume-1",
            matches=[
                strong_match(requirement("Experience with PostgreSQL"), "postgresql", ["experience:0:bullet:0"]),
                strong_match(requirement("Experience with FastAPI"), "fastapi", ["experience:0:bullet:1"]),
            ],
            created_at=now,
        )

        first = engine.scope(result, candidate)
        second = engine.scope(result, candidate)

        assert first == second


class TestClaimVerification:
    def test_rejects_hallucinated_technology(self):
        snapshot = resume()
        change = self._bullet_change(
            original="Built the ordering API with FastAPI",
            tailored="Built the ordering API with FastAPI and Kubernetes",
        )

        result = ClaimVerification().verify(change=change, snapshot=snapshot)

        assert result.passed is False
        assert any("kubernetes" in reason for reason in result.reasons)

    def test_rejects_invented_metric(self):
        snapshot = resume()
        change = self._bullet_change(
            original="Built the ordering API with FastAPI",
            tailored="Built the ordering API with FastAPI, reducing latency by 50%",
        )

        result = ClaimVerification().verify(change=change, snapshot=snapshot)

        assert result.passed is False
        assert any("50%" in reason for reason in result.reasons)

    def test_rejects_untraceable_employer(self):
        snapshot = resume(
            experience=[
                Experience(company="Acme", title="Engineer", start_date="2021-03", bullets=["Built the API"]),
                Experience(company="Beta Inc", title="Lead", start_date="2019-01", bullets=["Led a team"]),
            ]
        )
        change = self._bullet_change(
            original="Built the ordering API with FastAPI",
            tailored="Led the engineering org at Beta Inc building APIs",
            source_ids=["experience:0:bullet:0"],
        )

        result = ClaimVerification().verify(change=change, snapshot=snapshot)

        assert result.passed is False
        assert any("Beta Inc" in reason for reason in result.reasons)

    def test_passes_traceable_bullet(self):
        snapshot = resume()
        change = self._bullet_change(
            original="Built the ordering API with FastAPI",
            tailored="Built the ordering API with FastAPI",
        )

        result = ClaimVerification().verify(change=change, snapshot=snapshot)

        assert result.passed is True
        assert result.reasons == []

    def test_passes_traceable_project_bullet(self):
        snapshot = resume(
            projects=[
                Project(
                    name="Ordering service",
                    technologies=["FastAPI"],
                    bullets=["Built the service with FastAPI"],
                )
            ]
        )
        change = TailoredChange(
            key="project:0:bullet:0",
            kind=TailorChangeKind.BULLET,
            section="project",
            original="Built the service with FastAPI",
            tailored="Built the service with FastAPI",
            source_evidence_ids=["project:0:bullet:0"],
        )

        result = ClaimVerification().verify(change=change, snapshot=snapshot)

        assert result.passed is True
        assert result.reasons == []

    def test_rejects_project_bullet_with_hallucinated_technology(self):
        snapshot = resume(
            projects=[
                Project(
                    name="Ordering service",
                    technologies=["FastAPI"],
                    bullets=["Built the service with FastAPI"],
                )
            ]
        )
        change = TailoredChange(
            key="project:0:bullet:0",
            kind=TailorChangeKind.BULLET,
            section="project",
            original="Built the service with FastAPI",
            tailored="Built the service with FastAPI and Redis",
            source_evidence_ids=["project:0:bullet:0"],
        )

        result = ClaimVerification().verify(change=change, snapshot=snapshot)

        assert result.passed is False
        assert any("redis" in reason for reason in result.reasons)

    def test_rejects_bullet_without_source_evidence_ids(self):
        snapshot = resume()
        change = TailoredChange(
            key="experience:0:bullet:0",
            kind=TailorChangeKind.BULLET,
            section="experience",
            original="Built the ordering API with FastAPI",
            tailored="Built the ordering API with FastAPI",
            source_evidence_ids=[],
        )

        result = ClaimVerification().verify(change=change, snapshot=snapshot)

        assert result.passed is False
        assert any("source_evidence_ids" in reason for reason in result.reasons)

    @staticmethod
    def _bullet_change(*, original: str, tailored: str, source_ids: list[str] | None = None) -> TailoredChange:
        return TailoredChange(
            key="experience:0:bullet:0",
            kind=TailorChangeKind.BULLET,
            section="experience",
            original=original,
            tailored=tailored,
            source_evidence_ids=source_ids or ["experience:0:bullet:0"],
        )


class TestTailoringService:
    def test_tailor_captures_snapshot_and_pins_version(self):
        candidate = resume(
            experience=[
                Experience(
                    company="Acme",
                    title="Engineer",
                    start_date="2021-03",
                    bullets=["Built the ordering API with FastAPI"],
                )
            ]
        )
        service = make_service(resume_override=candidate)

        tailored = service.tailor("jd-1", "resume-1")

        assert tailored.resume_version_id
        assert tailored.resume_id == "resume-1"
        version = service._versions.get(tailored.resume_version_id)
        assert version is not None
        assert version.resume_id == "resume-1"
        assert version.data == candidate
        # master is untouched
        assert service._resumes.get("resume-1") == candidate
        assert service.get("jd-1") == tailored

    def test_tailor_is_immutable_against_later_master_changes(self):
        candidate = resume(
            summary="Original summary.",
            experience=[
                Experience(
                    company="Acme",
                    title="Engineer",
                    start_date="2021-03",
                    bullets=["Built the ordering API with FastAPI"],
                )
            ],
        )
        service = make_service(resume_override=candidate)
        tailored = service.tailor("jd-1", "resume-1")

        # the master changes after tailoring
        service._resumes.update("resume-1", candidate.model_copy(update={"summary": "Mutated summary."}))

        assert service.get("jd-1").summary == "Original summary."
        version = service._versions.get(tailored.resume_version_id)
        assert version.data.summary == "Original summary."

    def test_llm_rewrites_only_within_engine_scope(self):
        out_of_scope = RewrittenBullet(
            evidence_id="experience:9:bullet:0",
            text="HACKED: outside the scope",
            source_evidence_ids=["experience:9:bullet:0"],
        )
        in_scope = RewrittenBullet(
            evidence_id="experience:0:bullet:0",
            text="Reworded the FastAPI API build",
            reason="Reworded",
            source_evidence_ids=["experience:0:bullet:0"],
        )
        provider = FixtureLLMProvider(
            responses=[
                LLMTailoredOutput(
                    summary="Targeted summary",
                    summary_reason="rewrote",
                    summary_source_evidence_ids=["experience:0:bullet:0"],
                    bullets=[out_of_scope, in_scope],
                )
            ]
        )
        service = make_service(provider)

        tailored = service.tailor("jd-1", "resume-1")

        assert tailored.summary == "Targeted summary"
        assert tailored.experience[0].bullets[0] == "Reworded the FastAPI API build"
        assert "HACKED" not in tailored.experience[0].bullets[0]

    def test_every_rewritten_bullet_carries_source_evidence_ids(self):
        service = make_service()

        tailored = service.tailor("jd-1", "resume-1")

        for change in tailored.changes:
            assert change.source_evidence_ids, change.key
        for change in tailored.changes:
            if change.kind is TailorChangeKind.BULLET:
                assert change.source_evidence_ids[0] == change.key

    def test_tailored_resume_validates_against_schema(self):
        service = make_service()

        tailored = service.tailor("jd-1", "resume-1")

        restored = TailoredResume.model_validate(tailored.model_dump(mode="json"))
        assert restored == tailored

    def test_bad_llm_output_fails_cleanly_with_llm_validation_failed(self):
        provider = FixtureLLMProvider(
            responses=[{"bullets": "not-a-list"}, {"bullets": "not-a-list"}]
        )
        service = make_service(provider)

        with pytest.raises(LLMValidationFailed):
            service.tailor("jd-1", "resume-1")

    def test_hallucinated_technology_fails_with_tailoring_failed(self):
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
        service = make_service(provider)

        with pytest.raises(TailoringFailed) as exc:
            service.tailor("jd-1", "resume-1")
        assert "kubernetes" in str(exc.value.details)

    def test_invented_metric_fails_with_tailoring_failed(self):
        provider = FixtureLLMProvider(
            responses=[
                LLMTailoredOutput(
                    summary="Summary",
                    bullets=[
                        RewrittenBullet(
                            evidence_id="experience:0:bullet:0",
                            text="Built the ordering API with FastAPI, improving latency by 50%",
                            source_evidence_ids=["experience:0:bullet:0"],
                        )
                    ],
                )
            ]
        )
        service = make_service(provider)

        with pytest.raises(TailoringFailed):
            service.tailor("jd-1", "resume-1")

    def test_tailor_without_match_result_raises_not_found(self):
        versions = InMemoryRepository()
        tailored = InMemoryRepository()
        analyses = InMemoryRepository()
        matches = InMemoryRepository()
        service = TailoringService(
            version_repository=versions,
            tailored_repository=tailored,
            resume_repository=InMemoryResumeRepository(),
            analysis_repository=analyses,
            match_repository=matches,
            llm_provider=FixtureLLMProvider(),
        )

        with pytest.raises(NotFoundError):
            service.tailor("missing-jd", "resume-1")

    def test_apply_decisions_mutates_only_the_staged_resume(self):
        service = make_service()
        original_master = service._resumes.get("resume-1")
        service.tailor("jd-1", "resume-1")

        updated = service.apply_decisions(
            "jd-1",
            [
                ReviewDecision(key="experience:0:bullet:0", action=ChangeAction.reject),
                ReviewDecision(key="summary", action=ChangeAction.edit, text="Edited summary."),
            ],
        )

        by_key = {change.key: change for change in updated.changes}
        assert by_key["experience:0:bullet:0"].status == ChangeStatus.REJECTED
        assert updated.experience[0].bullets[0] == "Built the ordering API with FastAPI"
        assert by_key["summary"].status == ChangeStatus.EDITED
        assert updated.summary == "Edited summary."
        # master resume never mutated
        assert service._resumes.get("resume-1") == original_master

    def test_apply_decisions_unknown_key_raises(self):
        service = make_service()
        service.tailor("jd-1", "resume-1")

        from app.errors import ResourceValidationError

        with pytest.raises(ResourceValidationError):
            service.apply_decisions(
                "jd-1", [ReviewDecision(key="nope", action=ChangeAction.accept)]
            )

    def test_regenerate_change_rewrites_one_change_on_pinned_snapshot(self):
        service = make_service()
        original_master = service._resumes.get("resume-1")
        service.tailor("jd-1", "resume-1")
        initial = service.get("jd-1")

        regenerated = service.regenerate_change("jd-1", "summary")

        assert regenerated.resume_version_id == initial.resume_version_id
        assert regenerated.summary == "Backend engineer who builds API platforms."
        # master still untouched after regenerate
        assert service._resumes.get("resume-1") == original_master

    def test_regenerate_unknown_change_raises_not_found(self):
        service = make_service()
        service.tailor("jd-1", "resume-1")

        with pytest.raises(NotFoundError):
            service.regenerate_change("jd-1", "experience:9:bullet:0")

    def test_run_dispatches_tailor_and_regenerate_payloads(self):
        service = make_service()
        result = service.run({"job_description_id": "jd-1", "resume_id": "resume-1"})
        assert result["job_description_id"] == "jd-1"

        regenerated = service.run(
            {"job_description_id": "jd-1", "action": "regenerate", "change_key": "summary"}
        )
        assert regenerated["summary"] == "Backend engineer who builds API platforms."

    def test_full_pipeline_is_deterministic(self):
        service = make_service()

        first = service.tailor("jd-1", "resume-1")
        second = service.tailor("jd-1", "resume-1")

        assert first.experience == second.experience
        assert first.skills == second.skills
        assert [c.tailored for c in first.changes] == [c.tailored for c in second.changes]