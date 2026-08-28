import json
import re
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.domain.analysis import JobAnalysis, JobDescription, LLMJobAnalysis
from app.errors import LLMValidationFailed, NotFoundError, ResourceValidationError
from app.llm.base import JD_END_MARKER, JD_START_MARKER, LLMProvider
from app.repositories.base import EntityRepository
from app.time import utcnow

MAX_JD_LENGTH = 50_000
MAX_RETRIES = 1


class AnalysisService:
    """Job analysis: requirement extraction, classification, normalization."""

    def __init__(
        self,
        *,
        jd_repository: EntityRepository[JobDescription],
        analysis_repository: EntityRepository[JobAnalysis],
        llm_provider: LLMProvider,
    ) -> None:
        self._jd_repo = jd_repository
        self._analysis_repo = analysis_repository
        self._llm = llm_provider

    def create_job_description(
        self,
        *,
        company: str | None,
        role: str | None,
        location: str | None,
        jd_text: str,
    ) -> JobDescription:
        normalized = self.normalize_jd_text(jd_text)
        if not normalized:
            raise ResourceValidationError("job description text is required")
        if len(normalized) > MAX_JD_LENGTH:
            raise ResourceValidationError(
                "job description text is too long",
                details={"max_length": MAX_JD_LENGTH},
            )
        job_description = JobDescription(
            id=str(uuid4()),
            company=company,
            role=role,
            location=location,
            jd_text=normalized,
            created_at=utcnow(),
        )
        return self._jd_repo.add(job_description.id, job_description)

    def get_job_description(self, job_description_id: str) -> JobDescription:
        job_description = self._jd_repo.get(job_description_id)
        if job_description is None:
            raise NotFoundError(
                "job description not found", details={"id": job_description_id}
            )
        return job_description

    def analyze(self, jd_text: str) -> LLMJobAnalysis:
        """Run structured extraction with one controlled retry (ADR-0001)."""
        normalized = self.normalize_jd_text(jd_text)
        prompt = self._build_prompt(normalized)
        last_error: ValidationError | None = None
        for _attempt in range(MAX_RETRIES + 1):
            raw = self._llm.generate_structured(prompt=prompt, output_schema=LLMJobAnalysis)
            try:
                parsed = self._coerce(raw, LLMJobAnalysis)
            except ValidationError as exc:
                last_error = exc
                prompt = self._build_prompt(normalized, retry_error=exc)
                continue
            return self._normalize_analysis(parsed)
        raise LLMValidationFailed(
            "LLM returned structured output that failed validation",
            details={"validation_error": str(last_error)},
        )

    def analyze_job(self, job_description_id: str) -> JobAnalysis:
        """Analyze a persisted Job Description and store the result."""
        job_description = self.get_job_description(job_description_id)
        result = self.analyze(job_description.jd_text)
        record = JobAnalysis(
            id=job_description_id,
            job_description_id=job_description_id,
            role=result.role,
            seniority=result.seniority,
            requirements=result.requirements,
            created_at=utcnow(),
        )
        return self._analysis_repo.add(job_description_id, record)

    def get_analysis(self, job_description_id: str) -> JobAnalysis | None:
        return self._analysis_repo.get(job_description_id)

    @staticmethod
    def normalize_jd_text(text: str) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    @classmethod
    def _normalize_analysis(cls, analysis: LLMJobAnalysis) -> LLMJobAnalysis:
        seen: set[tuple[str, str]] = set()
        requirements = []
        for requirement in analysis.requirements:
            text = cls._collapse(requirement.requirement)
            key = (text.lower(), requirement.category.value)
            if key in seen:
                continue
            seen.add(key)
            requirements.append(
                requirement.model_copy(
                    update={"requirement": text, "context": cls._collapse(requirement.context)}
                )
            )
        return analysis.model_copy(update={"requirements": requirements})

    @staticmethod
    def _collapse(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _build_prompt(jd_text: str, *, retry_error: ValidationError | None = None) -> str:
        schema_json = json.dumps(LLMJobAnalysis.model_json_schema())
        prompt = (
            "Analyze the following job description and extract structured job requirements.\n"
            f"{JD_START_MARKER}\n{jd_text}\n{JD_END_MARKER}\n"
            "Return a single JSON object matching this schema exactly:\n"
            f"{schema_json}\n"
            "Each requirement keeps its original context (a short fragment of the JD), "
            "is classified as REQUIRED, PREFERRED, RESPONSIBILITY, SENIORITY, DOMAIN, or "
            "SOFT_SKILL, and carries importance HIGH, MEDIUM, or LOW."
        )
        if retry_error is not None:
            prompt += (
                "\nYour previous response failed validation and must not be repeated. "
                f"Return valid JSON matching the schema. Validation error: {retry_error}"
            )
        return prompt

    @staticmethod
    def _coerce(raw, schema: type[BaseModel]) -> BaseModel:
        if isinstance(raw, schema):
            return raw
        if isinstance(raw, BaseModel):
            raw = raw.model_dump()
        return schema.model_validate(raw)