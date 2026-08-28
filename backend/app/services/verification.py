import re

from pydantic import BaseModel, Field

from app import catalog
from app.domain.resume import Resume, evidence_ids
from app.domain.tailoring import TailorChangeKind, TailoredChange

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*%?")


class VerificationResult(BaseModel):
    """Outcome of Claim Verification for one rewritten change."""

    passed: bool
    reasons: list[str] = Field(default_factory=list)


class ClaimVerification:
    """Deterministic gate (ADR-0001): rejects any claim not traceable to evidence.

    For a rewritten bullet it checks technologies, numbers, employers, and
    titles against the source evidence the bullet itself cites. The summary
    is checked against the whole ResumeVersion snapshot — the master is the
    source of truth, so a summary claim is traceable when it appears anywhere
    in the snapshot.
    """

    def verify(self, *, change: TailoredChange, snapshot: Resume) -> VerificationResult:
        reasons: list[str] = []

        if change.kind is TailorChangeKind.BULLET and not change.source_evidence_ids:
            reasons.append("rewritten bullet carries no source_evidence_ids")

        source_text = self._source_text(change, snapshot)
        reasons.extend(self._technology_reasons(change.tailored, source_text))
        reasons.extend(self._number_reasons(change.tailored, source_text))
        reasons.extend(self._entity_reasons(change, snapshot))
        return VerificationResult(passed=not reasons, reasons=reasons)

    def _source_text(self, change: TailoredChange, snapshot: Resume) -> str:
        if change.kind is TailorChangeKind.SUMMARY:
            return self._snapshot_text(snapshot)
        ids = evidence_ids(snapshot)
        for proj_index, proj in enumerate(snapshot.projects):
            for bullet_index, bullet in enumerate(proj.bullets):
                ids[f"project:{proj_index}:bullet:{bullet_index}"] = bullet
        return "\n".join(ids[eid] for eid in change.source_evidence_ids if eid in ids)

    @staticmethod
    def _snapshot_text(snapshot: Resume) -> str:
        parts = [snapshot.summary]
        for skill_names in snapshot.skills.values():
            parts.extend(skill_names)
        for exp in snapshot.experience:
            parts.extend((exp.company, exp.title, exp.summary, *exp.bullets))
        for proj in snapshot.projects:
            parts.extend((proj.name, proj.description, *proj.bullets))
        for edu in snapshot.education:
            parts.append(edu.school)
        for cert in snapshot.certifications:
            parts.append(cert.name)
        return "\n".join(parts)

    @staticmethod
    def _technology_reasons(tailored: str, source_text: str) -> list[str]:
        traceable = set(catalog.skills_in_text(source_text))
        return [
            f"technology '{tech}' is not traceable to source evidence"
            for tech in catalog.skills_in_text(tailored)
            if tech not in traceable
        ]

    @staticmethod
    def _number_reasons(tailored: str, source_text: str) -> list[str]:
        return [
            f"number '{token}' is not traceable to source evidence"
            for token in _NUMBER_RE.findall(tailored)
            if token not in source_text
        ]

    def _entity_reasons(self, change: TailoredChange, snapshot: Resume) -> list[str]:
        if change.kind is TailorChangeKind.SUMMARY:
            return []
        owners = self._source_owners(change.source_evidence_ids)
        reasons: list[str] = []
        for exp_index, exp in enumerate(snapshot.experience):
            if exp.company and exp.company in change.tailored and exp_index not in owners:
                reasons.append(
                    f"employer '{exp.company}' is not traceable to source evidence"
                )
            if exp.title and exp.title in change.tailored and exp_index not in owners:
                reasons.append(f"title '{exp.title}' is not traceable to source evidence")
        return reasons

    @staticmethod
    def _source_owners(source_evidence_ids: list[str]) -> set[int]:
        owners: set[int] = set()
        for evidence_id in source_evidence_ids:
            match = re.match(r"experience:(\d+)(?::|$)", evidence_id)
            if match is not None:
                owners.add(int(match.group(1)))
        return owners