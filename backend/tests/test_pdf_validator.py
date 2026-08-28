"""PdfValidator: pdftotext extraction, page count, name/contact, headings,
reading order, character integrity, content preservation, and layout measures.

Covers the T7 acceptance criteria for validation: extraction, headings,
name/contact, page count, and corrupted output — plus single-column, tables,
and graphics measurement. Real-compilation tests skip when pdflatex/pdftotext
are not installed (CI carries them).
"""

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.resume import Experience, MonthYear, PersonalInformation
from app.domain.tailoring import TailoredResume
from app.errors import PdfValidationFailed
from app.pdf.tools import PdfToolError
from app.pdf.validator import PdfValidator

pdflatex_available = pytest.mark.skipif(
    shutil.which("pdflatex") is None, reason="pdflatex not installed"
)
pdftotext_available = pytest.mark.skipif(
    shutil.which("pdftotext") is None, reason="pdftotext not installed"
)


class FakeTools:
    """Scripted pdf tool responses; a PdfToolError simulates a broken PDF."""

    def __init__(
        self,
        text: str = "",
        *,
        pages: int = 1,
        images: int = 0,
        fail_extract: bool = False,
        fail_pages: bool = False,
        fail_images: bool = False,
    ) -> None:
        self.text = text
        self.pages = pages
        self.images = images
        self.fail_extract = fail_extract
        self.fail_pages = fail_pages
        self.fail_images = fail_images

    def extract_text(self, pdf_bytes: bytes) -> str:
        if self.fail_extract:
            raise PdfToolError("pdftotext failed with exit code 1")
        return self.text

    def page_count(self, pdf_bytes: bytes) -> int:
        if self.fail_pages:
            raise PdfToolError("pdfinfo failed")
        return self.pages

    def image_count(self, pdf_bytes: bytes) -> int:
        if self.fail_images:
            raise PdfToolError("pdfimages failed")
        return self.images


def _tailored() -> TailoredResume:
    return TailoredResume(
        job_description_id="jd-1",
        resume_version_id="rv-1",
        resume_id="r-1",
        personal_information=PersonalInformation(
            full_name="Ada Lovelace", email="ada@example.com"
        ),
        summary="Backend engineer who builds API platforms with FastAPI.",
        skills={"Frameworks": ["FastAPI"]},
        experience=[
            Experience(
                company="Acme",
                title="Engineer",
                start_date=MonthYear("2021-05"),
                bullets=["Built the ordering API with FastAPI and PostgreSQL."],
            )
        ],
        created_at=datetime.now(UTC),
    )


def _valid_text() -> str:
    # Mirrors pdftotext -layout output for the _tailored resume: a wide header,
    # headings on their own lines, and mostly full-width content lines.
    return (
        "Ada Lovelace Backend Engineer ada@example.com | 555-0100 | London UK\n"
        "Summary\n"
        "Backend engineer who builds API platforms with FastAPI.\n"
        "Skills\n"
        "Frameworks FastAPI, Flask, Django, PostgreSQL\n"
        "Experience\n"
        "Engineer May 2021 -- Present Acme, London\n"
        "Built the ordering API with FastAPI and PostgreSQL.\n"
    )


def _validator(tools: FakeTools) -> PdfValidator:
    return PdfValidator(tools=tools)


def test_valid_pdf_is_measured_into_a_report() -> None:
    tools = FakeTools(text=_valid_text(), pages=1, images=0)
    report = _validator(tools).validate(b"%PDF-1.4", _tailored())

    assert report.page_count == 1
    assert report.single_column is True
    assert report.standard_headings is True
    assert report.critical_info_in_body is True
    assert report.unexpected_tables == 0
    assert report.unexpected_graphics == 0
    assert "Ada Lovelace" in report.extracted_text


def test_corrupted_output_returns_structured_pdf_validation_failed() -> None:
    tools = FakeTools(fail_extract=True)
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"corrupt", _tailored())
    assert excinfo.value.code == "PDF_VALIDATION_FAILED"
    assert excinfo.value.status_code == 502


def test_empty_extraction_returns_pdf_validation_failed() -> None:
    tools = FakeTools(text="   \n  ")
    with pytest.raises(PdfValidationFailed):
        _validator(tools).validate(b"%PDF-1.4", _tailored())


def test_page_count_outside_expected_range_fails() -> None:
    tools = FakeTools(text=_valid_text(), pages=3)
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert "page count" in excinfo.value.message


def test_early_career_resume_overflowing_one_page_fails() -> None:
    tailored = _tailored().model_copy(
        update={"experience": [], "projects": []}
    )
    tools = FakeTools(text=_valid_text(), pages=2)
    with pytest.raises(PdfValidationFailed):
        _validator(tools).validate(b"%PDF-1.4", tailored)


def test_missing_candidate_name_fails() -> None:
    tools = FakeTools(text=_valid_text().replace("Ada Lovelace", "Someone Else"))
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert "name" in excinfo.value.message


def test_missing_contact_information_fails() -> None:
    tools = FakeTools(text=_valid_text().replace("ada@example.com", ""))
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert "contact" in excinfo.value.message


def test_missing_section_heading_fails() -> None:
    tools = FakeTools(text=_valid_text().replace("Experience\n", ""))
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert excinfo.value.details["heading"] == "Experience"


def test_headings_out_of_reading_order_fail() -> None:
    scrambled = (
        _valid_text()
        .replace("Skills\nFrameworks", "Experience\nFrameworks")
        .replace("Experience\nEngineer", "Skills\nEngineer")
    )
    tools = FakeTools(text=scrambled)
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert "reading order" in excinfo.value.message


def test_character_integrity_rejects_latex_leaked_into_text() -> None:
    tools = FakeTools(text=_valid_text() + r"\textbf{Engineer}")
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert "LaTeX command" in excinfo.value.message


def test_content_preservation_rejects_a_lost_bullet() -> None:
    tools = FakeTools(
        text=_valid_text().replace(
            "Built the ordering API with FastAPI and PostgreSQL.", ""
        )
    )
    with pytest.raises(PdfValidationFailed) as excinfo:
        _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert "preserve" in excinfo.value.message


def test_content_preservation_tolerates_line_wrapping() -> None:
    wrapped = _valid_text().replace(
        "Built the ordering API with FastAPI and PostgreSQL.",
        "Built the ordering API with FastAPI and\n    PostgreSQL.",
    )
    tools = FakeTools(text=wrapped)
    report = _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert report.critical_info_in_body is True


def test_single_column_measures_short_two_column_lines() -> None:
    short = _tailored().model_copy(
        update={
            "summary": "Short summary.",
            "experience": [
                Experience(
                    company="Acme",
                    title="Engineer",
                    start_date=MonthYear("2021-05"),
                    bullets=["Short bullet."],
                )
            ],
        }
    )
    two_column = (
        "Ada Lovelace ada@example.com\n"
        "Summary\n"
        "Short summary.\n"
        "Skills\n"
        "Python\n"
        "FastAPI\n"
        "SQL\n"
        "Docker\n"
        "Experience\n"
        "Engineer\n"
        "Short bullet."
    )
    report = _validator(FakeTools(text=two_column)).validate(b"%PDF-1.4", short)
    assert report.single_column is False


def test_unexpected_tables_counts_tab_separated_regions() -> None:
    tools = FakeTools(text=_valid_text() + "Role\tEngineer\nCompany\tAcme")
    report = _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert report.unexpected_tables == 2


def test_unexpected_graphics_counts_embedded_images() -> None:
    tools = FakeTools(text=_valid_text(), images=2)
    report = _validator(tools).validate(b"%PDF-1.4", _tailored())
    assert report.unexpected_graphics == 2


@pdflatex_available
@pdftotext_available
def test_real_pdf_round_trip_validates_cleanly(tmp_path: Path) -> None:
    from app.latex.compiler import LatexCompiler
    from app.latex.render import LatexRenderingService

    tex = LatexRenderingService().render(_tailored())
    pdf = LatexCompiler(timeout=60.0).compile(tex, tmp_path)

    report = PdfValidator().validate(pdf.read_bytes(), _tailored())

    assert report.page_count == 1
    assert report.single_column is True
    assert report.standard_headings is True
    assert report.critical_info_in_body is True
    assert report.unexpected_tables == 0
    assert report.unexpected_graphics == 0
    assert "Ada Lovelace" in report.extracted_text
    assert "Experience" in report.extracted_text
    assert "Built the ordering API with FastAPI and PostgreSQL." in report.extracted_text