"""Poppler-utils subprocess wrappers: pdftotext, pdfinfo, pdfimages.

The PDF seam of the pipeline: extraction and measurement run as subprocess
argument arrays inside an isolated temporary directory with a timeout — never
a shell (user story 24). Failures surface as PdfToolError, which the validator
maps to a structured PDF_VALIDATION_FAILED.
"""

import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

_PAGES_RE = re.compile(r"^Pages:\s*(\d+)\s*$", re.IGNORECASE | re.MULTILINE)
_IMAGE_ROW_RE = re.compile(r"^\s*\d+\s+\d+\s+")


class PdfToolError(Exception):
    """A poppler-utils tool failed (timeout, nonzero exit, missing output)."""


class PdfTools:
    """Thin wrappers over pdftotext / pdfinfo / pdfimages."""

    def __init__(
        self,
        *,
        pdftotext: str = "pdftotext",
        pdfinfo: str = "pdfinfo",
        pdfimages: str = "pdfimages",
        timeout: float = 30.0,
    ) -> None:
        self._pdftotext = pdftotext
        self._pdfinfo = pdfinfo
        self._pdfimages = pdfimages
        self._timeout = timeout

    def extract_text(self, pdf_bytes: bytes) -> str:
        with self._temp_pdf(pdf_bytes) as pdf_path:
            proc = self._run(
                [self._pdftotext, "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
                "pdftotext",
            )
        return proc.stdout.decode("utf-8", errors="replace")

    def page_count(self, pdf_bytes: bytes) -> int:
        with self._temp_pdf(pdf_bytes) as pdf_path:
            proc = self._run([self._pdfinfo, str(pdf_path)], "pdfinfo")
        match = _PAGES_RE.search(proc.stdout.decode("utf-8", errors="replace"))
        if match is None:
            raise PdfToolError("pdfinfo reported no page count")
        return int(match.group(1))

    def image_count(self, pdf_bytes: bytes) -> int:
        with self._temp_pdf(pdf_bytes) as pdf_path:
            proc = self._run([self._pdfimages, "-list", str(pdf_path)], "pdfimages")
        output = proc.stdout.decode("utf-8", errors="replace")
        return len([line for line in output.splitlines() if _IMAGE_ROW_RE.match(line)])

    @contextmanager
    def _temp_pdf(self, pdf_bytes: bytes):
        with tempfile.TemporaryDirectory(prefix="ats-pdf-") as work_dir:
            pdf_path = Path(work_dir) / "input.pdf"
            pdf_path.write_bytes(pdf_bytes)
            yield pdf_path

    def _run(self, args: list[str], label: str) -> subprocess.CompletedProcess:
        try:
            proc = subprocess.run(
                args, capture_output=True, timeout=self._timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfToolError(f"{label} timed out") from exc
        if proc.returncode != 0:
            raise PdfToolError(f"{label} failed with exit code {proc.returncode}")
        return proc