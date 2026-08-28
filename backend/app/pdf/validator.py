"""PDF validation gate for generated resumes (user story 25).

Every generated PDF is extracted with pdftotext and checked for validity,
expected page count, presence of name/contact, standard headings in reading
order, character integrity, and content preservation. Any failure raises
PDF_VALIDATION_FAILED — a broken PDF is never presented as final. Layout
properties (single-column, unexpected tables/graphics) are measured for the
ATS Compatibility Analysis rather than treated as hard gates.
"""

import re

from pydantic import BaseModel

from app.domain.tailoring import TailoredResume
from app.errors import PdfValidationFailed
from app.pdf.tools import PdfToolError, PdfTools

_WS_RE = re.compile(r"\s+")
_DEHYPHEN_RE = re.compile(r"-\s*\n\s*")
_HEADING_RE = r"(?im)^\s*{title}\s*$"
_LATEX_LEAK_TOKENS = (
    "\\documentclass",
    "\\begin{",
    "\\end{",
    "\\section",
    "\\item",
    "\\textbf",
    "\\textit",
    "\\textbackslash",
    "\\href",
)


class PdfValidationReport(BaseModel):
    """Measured results of the PDF validation gate, consumed by the ATS analysis."""

    extracted_text: str
    page_count: int
    single_column: bool
    standard_headings: bool
    critical_info_in_body: bool
    unexpected_tables: int
    unexpected_graphics: int


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _contains(haystack: str, needle: str) -> bool:
    return needle in haystack


class PdfValidator:
    """Extracts a compiled PDF and validates it against the Tailored Resume it renders."""

    def __init__(self, *, tools: PdfTools | None = None) -> None:
        self._tools = tools or PdfTools()

    def validate(
        self, pdf_bytes: bytes, tailored: TailoredResume
    ) -> PdfValidationReport:
        try:
            text = self._tools.extract_text(pdf_bytes)
            page_count = self._tools.page_count(pdf_bytes)
            image_count = self._tools.image_count(pdf_bytes)
        except PdfToolError as exc:
            raise PdfValidationFailed(
                "PDF could not be extracted or measured",
                details={"error": str(exc)},
            ) from exc

        self._check_extraction(text)
        self._check_page_count(page_count, tailored)
        self._check_name_and_contact(text, tailored)
        self._check_headings(text, tailored)
        self._check_character_integrity(text)
        self._check_content_preserved(text, tailored)

        return PdfValidationReport(
            extracted_text=text,
            page_count=page_count,
            single_column=self._is_single_column(text),
            standard_headings=True,
            critical_info_in_body=True,
            unexpected_tables=text.count("\t"),
            unexpected_graphics=image_count,
        )

    @staticmethod
    def _check_extraction(text: str) -> None:
        if not text.strip():
            raise PdfValidationFailed(
                "pdftotext extracted no text", details={"output": "empty"}
            )

    def _check_page_count(self, page_count: int, tailored: TailoredResume) -> None:
        expected = self._expected_pages(tailored)
        if not 1 <= page_count <= expected:
            raise PdfValidationFailed(
                f"page count {page_count} is outside the expected range 1..{expected}",
                details={"page_count": page_count, "expected_max": expected},
            )

    @staticmethod
    def _expected_pages(tailored: TailoredResume) -> int:
        # 1 page early-career, up to 2 for experienced; never auto-fitted
        # (user story 33). Reported honestly, never shrunk to fit.
        if not tailored.experience and not tailored.projects:
            return 1
        return 2

    @staticmethod
    def _check_name_and_contact(text: str, tailored: TailoredResume) -> None:
        normalized = _normalize(text)
        info = tailored.personal_information
        if info.full_name and not _contains(
            normalized, _normalize(info.full_name)
        ):
            raise PdfValidationFailed(
                "candidate name missing from extracted PDF text",
                details={"expected": info.full_name},
            )
        contact_items = [
            item for item in (info.email, info.phone, info.location, info.website) if item
        ]
        if contact_items and not any(
            _contains(normalized, _normalize(item)) for item in contact_items
        ):
            raise PdfValidationFailed(
                "no contact information found in extracted PDF text",
                details={"expected": contact_items},
            )

    @staticmethod
    def _check_headings(text: str, tailored: TailoredResume) -> None:
        present = [
            title
            for title, has_content in (
                ("Summary", bool(tailored.summary)),
                ("Skills", bool(tailored.skills)),
                ("Experience", bool(tailored.experience)),
                ("Projects", bool(tailored.projects)),
                ("Education", bool(tailored.education)),
                ("Certifications", bool(tailored.certifications)),
            )
            if has_content
        ]
        positions = []
        for title in present:
            match = re.search(_HEADING_RE.format(title=re.escape(title)), text)
            if match is None:
                raise PdfValidationFailed(
                    f"section heading {title!r} missing from extracted PDF text",
                    details={"heading": title},
                )
            positions.append(match.start())
        if positions != sorted(positions):
            raise PdfValidationFailed(
                "section headings appear out of reading order",
                details={"sections": present},
            )

    @staticmethod
    def _check_character_integrity(text: str) -> None:
        for token in _LATEX_LEAK_TOKENS:
            if token in text:
                raise PdfValidationFailed(
                    f"LaTeX command leaked into extracted PDF text: {token!r}",
                    details={"token": token},
                )

    @staticmethod
    def _check_content_preserved(text: str, tailored: TailoredResume) -> None:
        candidates: list[str] = []
        if tailored.summary:
            candidates.append(tailored.summary)
        for exp in tailored.experience:
            candidates.extend(exp.bullets)
        for proj in tailored.projects:
            candidates.extend(proj.bullets)
        haystacks = [
            _normalize(text),
            _normalize(_DEHYPHEN_RE.sub("", text)),
        ]
        for candidate in candidates:
            needle = _normalize(candidate)
            if not any(_contains(haystack, needle) for haystack in haystacks):
                raise PdfValidationFailed(
                    "PDF text does not preserve the tailored content",
                    details={"content": candidate},
                )

    @staticmethod
    def _is_single_column(text: str) -> bool:
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if not lines:
            return True
        wide = sum(1 for line in lines if len(line) >= 40)
        return wide / len(lines) >= 0.5