"""Domain entity <-> SQLAlchemy row mappers (ADR-0001 layering).

Services speak in pydantic domain objects; the DB repository persists
rows. These converters bridge the two so persistence is explicit and the
generic ``SqlAlchemyRepository`` never sees an unmapped object.
"""

from app import models
from app.domain.analysis import JobAnalysis, JobDescription
from app.domain.generated import GeneratedResume
from app.domain.jobs import Job
from app.domain.matching import EvidenceMatch, MatchResult
from app.domain.resume import Resume
from app.domain.tailoring import TailoredResume
from app.domain.versioning import ResumeVersion


def job_description_to_row(entity: JobDescription) -> models.JobDescription:
    return models.JobDescription(
        id=entity.id,
        company=entity.company,
        role=entity.role,
        location=entity.location,
        jd_text=entity.jd_text,
        created_at=entity.created_at,
    )


def job_description_from_row(row: models.JobDescription) -> JobDescription:
    return JobDescription(
        id=row.id,
        company=row.company,
        role=row.role,
        location=row.location,
        jd_text=row.jd_text,
        created_at=row.created_at,
    )


def job_analysis_to_row(entity: JobAnalysis) -> models.JobAnalysis:
    return models.JobAnalysis(
        id=entity.id,
        job_description_id=entity.job_description_id,
        role=entity.role,
        seniority=entity.seniority,
        requirements=[r.model_dump(mode="json") for r in entity.requirements],
        created_at=entity.created_at,
    )


def job_analysis_from_row(row: models.JobAnalysis) -> JobAnalysis:
    return JobAnalysis(
        id=row.id,
        job_description_id=row.job_description_id,
        role=row.role,
        seniority=row.seniority,
        requirements=row.requirements,
        created_at=row.created_at,
    )


def job_to_row(entity: Job) -> models.Job:
    return models.Job(
        id=entity.id,
        type=entity.type,
        status=entity.status,
        payload=entity.payload,
        result=entity.result,
        error_code=entity.error_code,
        error_message=entity.error_message,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def job_from_row(row: models.Job) -> Job:
    return Job(
        id=row.id,
        type=row.type,
        status=row.status,
        payload=row.payload,
        result=row.result,
        error_code=row.error_code,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def match_result_to_row(entity: MatchResult) -> models.MatchResultRow:
    return models.MatchResultRow(
        id=entity.job_description_id,
        job_description_id=entity.job_description_id,
        resume_id=entity.resume_id,
        matches=[m.model_dump(mode="json") for m in entity.matches],
        created_at=entity.created_at,
    )


def match_result_from_row(row: models.MatchResultRow) -> MatchResult:
    return MatchResult(
        job_description_id=row.job_description_id,
        resume_id=row.resume_id,
        matches=[EvidenceMatch.model_validate(m) for m in row.matches],
        created_at=row.created_at,
    )


def resume_version_to_row(entity: ResumeVersion) -> models.ResumeVersionRow:
    return models.ResumeVersionRow(
        id=entity.id,
        resume_id=entity.resume_id,
        data=entity.data.model_dump(exclude={"id"}, mode="json"),
        created_at=entity.created_at,
    )


def resume_version_from_row(row: models.ResumeVersionRow) -> ResumeVersion:
    return ResumeVersion(
        id=row.id,
        resume_id=row.resume_id,
        data=Resume.model_validate({**row.data, "id": row.resume_id}),
        created_at=row.created_at,
    )


def tailored_resume_to_row(entity: TailoredResume) -> models.TailoredResumeRow:
    return models.TailoredResumeRow(
        id=entity.job_description_id,
        job_description_id=entity.job_description_id,
        resume_version_id=entity.resume_version_id,
        resume_id=entity.resume_id,
        data=entity.model_dump(mode="json"),
        created_at=entity.created_at,
    )


def tailored_resume_from_row(row: models.TailoredResumeRow) -> TailoredResume:
    return TailoredResume.model_validate(row.data)


def generated_resume_to_row(entity: GeneratedResume) -> models.GeneratedResumeRow:
    return models.GeneratedResumeRow(
        id=entity.job_description_id,
        job_description_id=entity.job_description_id,
        resume_version_id=entity.resume_version_id,
        resume_id=entity.resume_id,
        data=entity.model_dump(mode="json"),
        created_at=entity.created_at,
    )


def generated_resume_from_row(row: models.GeneratedResumeRow) -> GeneratedResume:
    return GeneratedResume.model_validate(row.data)