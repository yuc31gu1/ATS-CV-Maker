"""GENERATE stage: render, compile, validate, and analyze the Tailored Resume."""

import tempfile
from pathlib import Path

from app.domain.generated import GeneratedResume
from app.domain.tailoring import TailoredResume
from app.errors import NotFoundError, StorageFileNotFound
from app.latex.compiler import LatexCompiler
from app.latex.render import LatexRenderingService
from app.pdf.validator import PdfValidator
from app.repositories.base import EntityRepository
from app.services.ats import AtsAnalysisService
from app.storage.base import StorageService
from app.time import utcnow


class GenerationService:
    """Deterministic, synchronous document generation (ADR-0003).

    Renders the Tailored Resume through LatexRenderingService, compiles with
    pdflatex in an isolated temp directory, then validates the PDF through
    PdfValidator before it can be presented as final (T7). A validated PDF is
    measured into an ATS Compatibility Analysis via AtsAnalysisService; both
    the ``.tex`` source and the PDF are stored through the StorageService
    abstraction. Files are keyed by the job description id (the stepper
    session root); the persisted bundle pins to the Tailored Resume's
    ResumeVersion (ADR-0004).
    """

    def __init__(
        self,
        *,
        tailored_repository: EntityRepository[TailoredResume],
        generated_repository: EntityRepository[GeneratedResume],
        storage: StorageService,
        ats: AtsAnalysisService,
        renderer: LatexRenderingService | None = None,
        compiler: LatexCompiler | None = None,
        validator: PdfValidator | None = None,
    ) -> None:
        self._tailored = tailored_repository
        self._generated = generated_repository
        self._storage = storage
        self._ats = ats
        self._renderer = renderer or LatexRenderingService()
        self._compiler = compiler or LatexCompiler()
        self._validator = validator or PdfValidator()

    def get(self, job_description_id: str) -> GeneratedResume | None:
        return self._generated.get(job_description_id)

    def generate(self, job_description_id: str) -> GeneratedResume:
        tailored = self._tailored.get(job_description_id)
        if tailored is None:
            raise NotFoundError(
                "tailored resume not found",
                details={"job_description_id": job_description_id},
            )
        tex = self._renderer.render(tailored)
        pdf_bytes = self._compile(tex)
        report = self._validator.validate(pdf_bytes, tailored)
        analysis = self._ats.analyze(job_description_id, tailored, report)
        latex_key = f"latex/{job_description_id}.tex"
        pdf_key = f"pdf/{job_description_id}.pdf"
        self._storage.save(latex_key, tex.encode("utf-8"))
        self._storage.save(pdf_key, pdf_bytes)
        generated = GeneratedResume(
            job_description_id=job_description_id,
            resume_version_id=tailored.resume_version_id,
            resume_id=tailored.resume_id,
            latex_key=latex_key,
            pdf_key=pdf_key,
            ats_analysis=analysis,
            created_at=utcnow(),
        )
        return self._generated.add(job_description_id, generated)

    def _compile(self, tex: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="ats-latex-") as work_dir:
            pdf_path = self._compiler.compile(tex, Path(work_dir))
            return pdf_path.read_bytes()

    def latex_bytes(self, generated: GeneratedResume) -> bytes:
        return self._load(generated.latex_key, "latex source")

    def pdf_bytes(self, generated: GeneratedResume) -> bytes:
        return self._load(generated.pdf_key, "PDF")

    def _load(self, key: str, label: str) -> bytes:
        try:
            return self._storage.load(key)
        except OSError as exc:
            raise StorageFileNotFound(
                f"stored {label} missing",
                details={"key": key},
            ) from exc