from app.domain.analysis import JobAnalysis, JobDescription
from app.domain.dashboard import ApplicationSummary, DashboardSummary
from app.domain.generated import GeneratedResume
from app.domain.tailoring import TailoredResume
from app.repositories.base import EntityRepository
from app.repositories.resume import ResumeRepository


class DashboardService:
    """Read model for the dashboard and /history (product UX, T8).

    Combines the staged rows behind each stepper session — the Job
    Description root plus its Job Analysis, Tailored Resume, and Generated
    Resume — into the counts and application summaries the dashboard and
    history pages need. Read-only; never runs LLM jobs.
    """

    def __init__(
        self,
        *,
        resume_repository: ResumeRepository,
        jd_repository: EntityRepository[JobDescription],
        analysis_repository: EntityRepository[JobAnalysis],
        tailored_repository: EntityRepository[TailoredResume],
        generated_repository: EntityRepository[GeneratedResume],
    ) -> None:
        self._resumes = resume_repository
        self._jds = jd_repository
        self._analyses = analysis_repository
        self._tailored = tailored_repository
        self._generated = generated_repository

    def list_applications(self) -> list[ApplicationSummary]:
        """All stepper sessions, newest first, with their reached stages."""
        analyses = {item.job_description_id for item in self._analyses.list()}
        tailored = {item.job_description_id for item in self._tailored.list()}
        generated = {item.job_description_id for item in self._generated.list()}
        applications = [
            ApplicationSummary(
                job_description_id=jd.id,
                company=jd.company,
                role=jd.role,
                location=jd.location,
                created_at=jd.created_at,
                has_analysis=jd.id in analyses,
                has_tailored=jd.id in tailored,
                has_generated=jd.id in generated,
            )
            for jd in self._jds.list()
        ]
        return sorted(applications, key=lambda app: app.created_at, reverse=True)

    def summary(self) -> DashboardSummary:
        resumes = self._resumes.list()
        master_resume = resumes[0] if resumes else None
        return DashboardSummary(
            master_resume=master_resume,
            tailored_cv_count=len(self._tailored.list()),
            analyzed_jobs_count=len(self._analyses.list()),
            recent_applications=self.list_applications(),
        )