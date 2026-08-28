"""GenerationService: render -> compile -> store through StorageService."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.generated import GeneratedResume
from app.domain.resume import Experience, MonthYear, PersonalInformation
from app.domain.tailoring import TailoredResume
from app.errors import NotFoundError, StorageFileNotFound
from app.latex.compiler import LatexCompiler
from app.repositories.in_memory import InMemoryRepository
from app.services.generation import GenerationService
from app.storage.base import StorageService
from app.storage.local import LocalStorageService


class FakeCompiler:
    """Produces a tiny but readable PDF without invoking pdflatex."""

    def __init__(self, *, produce: bool = True, corrupt: bool = False) -> None:
        self.produce = produce
        self.corrupt = corrupt
        self.last_tex: str | None = None

    def compile(self, tex: str, work_dir: Path) -> Path:
        self.last_tex = tex
        pdf = work_dir / "main.pdf"
        if not self.produce:
            return pdf
        pdf.write_bytes(b"corrupt-bytes" if self.corrupt else b"%PDF-1.4 fake output")
        return pdf


class SwappableStorage:
    """A non-Local StorageService implementation proving swappability."""

    def __init__(self) -> None:
        self._items: dict[str, bytes] = {}

    def save(self, key: str, data: bytes) -> Path:
        self._items[key] = data
        return Path(key)

    def load(self, key: str) -> bytes:
        if key not in self._items:
            raise FileNotFoundError(key)
        return self._items[key]

    def delete(self, key: str) -> None:
        self._items.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self._items


def _tailored(job_description_id: str = "jd-1") -> TailoredResume:
    return TailoredResume(
        job_description_id=job_description_id,
        resume_version_id="rv-1",
        resume_id="r-1",
        personal_information=PersonalInformation(full_name="Ada Lovelace"),
        summary="Built the ordering API with FastAPI.",
        skills={"Frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date=MonthYear("2021-03"),
                bullets=["Built the ordering API with FastAPI."],
            )
        ],
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def service(tmp_path) -> tuple[GenerationService, InMemoryRepository, LocalStorageService]:
    tailored_repo = InMemoryRepository()
    generated_repo = InMemoryRepository()
    storage = LocalStorageService(tmp_path / "storage")
    svc = GenerationService(
        tailored_repository=tailored_repo,
        generated_repository=generated_repo,
        storage=storage,
        compiler=FakeCompiler(),
    )
    return svc, tailored_repo, storage


def test_generate_stores_tex_and_pdf_and_persists_bundle(service):
    svc, tailored_repo, storage = service
    tailored_repo.add("jd-1", _tailored())

    generated = svc.generate("jd-1")

    assert isinstance(generated, GeneratedResume)
    assert generated.job_description_id == "jd-1"
    assert generated.resume_version_id == "rv-1"
    assert generated.resume_id == "r-1"
    assert generated.latex_key == "latex/jd-1.tex"
    assert generated.pdf_key == "pdf/jd-1.pdf"
    assert storage.exists("latex/jd-1.tex")
    assert storage.exists("pdf/jd-1.pdf")
    assert storage.load("latex/jd-1.tex").startswith(b"\\documentclass")
    assert storage.load("pdf/jd-1.pdf").startswith(b"%PDF")
    assert svc.get("jd-1") == generated


def test_generate_rejects_missing_tailored(service):
    svc, _, _ = service
    with pytest.raises(NotFoundError):
        svc.generate("jd-missing")


def test_generate_is_deterministic_across_runs(service):
    svc, tailored_repo, storage = service
    tailored_repo.add("jd-1", _tailored())
    first = svc.generate("jd-1")
    first_tex = storage.load("latex/jd-1.tex")
    first_pdf = storage.load("pdf/jd-1.pdf")
    second = svc.generate("jd-1")
    assert second.resume_version_id == first.resume_version_id
    assert second.latex_key == first.latex_key
    assert second.pdf_key == first.pdf_key
    assert storage.load("latex/jd-1.tex") == first_tex
    assert storage.load("pdf/jd-1.pdf") == first_pdf


def test_pdf_and_latex_bytes_are_downloadable(service):
    svc, tailored_repo, _ = service
    tailored_repo.add("jd-1", _tailored())
    generated = svc.generate("jd-1")
    assert svc.pdf_bytes(generated).startswith(b"%PDF")
    assert svc.latex_bytes(generated).startswith(b"\\documentclass")


def test_missing_stored_file_returns_file_not_found(service):
    svc, _, _ = service
    generated = GeneratedResume(
        job_description_id="jd-1",
        resume_version_id="rv-1",
        resume_id="r-1",
        latex_key="latex/jd-1.tex",
        pdf_key="pdf/jd-1.pdf",
        created_at=datetime.now(UTC),
    )
    with pytest.raises(StorageFileNotFound) as excinfo:
        svc.latex_bytes(generated)
    assert excinfo.value.code == "FILE_NOT_FOUND"
    assert excinfo.value.status_code == 404


def test_storage_is_swappable_without_redesign(tmp_path):
    tailored_repo = InMemoryRepository()
    generated_repo = InMemoryRepository()
    storage = SwappableStorage()
    assert isinstance(storage, StorageService)
    svc = GenerationService(
        tailored_repository=tailored_repo,
        generated_repository=generated_repo,
        storage=storage,
        compiler=FakeCompiler(),
    )
    tailored_repo.add("jd-1", _tailored())

    generated = svc.generate("jd-1")

    assert storage.exists("latex/jd-1.tex")
    assert storage.exists("pdf/jd-1.pdf")
    assert svc.pdf_bytes(generated).startswith(b"%PDF")
    assert svc.latex_bytes(generated).startswith(b"\\documentclass")


@__import__("pytest").mark.skipif(
    __import__("shutil").which("pdflatex") is None, reason="pdflatex not installed"
)
def test_generate_compiles_a_real_pdf(tmp_path):
    """End-to-end service generation through real pdflatex."""
    tailored_repo = InMemoryRepository()
    generated_repo = InMemoryRepository()
    svc = GenerationService(
        tailored_repository=tailored_repo,
        generated_repository=generated_repo,
        storage=LocalStorageService(tmp_path / "storage"),
        compiler=LatexCompiler(timeout=60.0),
    )
    tailored_repo.add("jd-1", _tailored())

    generated = svc.generate("jd-1")

    pdf = svc.pdf_bytes(generated)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000