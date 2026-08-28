"""LatexCompiler: pdflatex in an isolated temp dir, via argument arrays.

Covers the T6 acceptance criteria for compilation: success, Unicode, and
corrupted/missing output, all returning LATEX_COMPILATION_FAILED on failure.
Real-compilation tests skip when pdflatex is not installed (CI carries it).
"""

import subprocess
from pathlib import Path

import pytest

from app.errors import LatexCompilationFailed
from app.latex.compiler import LatexCompiler

pdflatex_available = pytest.mark.skipif(
    __import__("shutil").which("pdflatex") is None, reason="pdflatex not installed"
)


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    work_dir = tmp_path / "compile"
    work_dir.mkdir()
    return work_dir


@pytest.fixture
def compiler() -> LatexCompiler:
    return LatexCompiler(timeout=60.0)


SIMPLE_TEX = r"""\documentclass[10pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[hidelinks]{hyperref}
\begin{document}
\section*{Summary}
Built the ordering API with FastAPI.
\end{document}
"""


@pdflatex_available
def test_compile_produces_a_nonempty_pdf(compiler: LatexCompiler, work_dir: Path):
    pdf = compiler.compile(SIMPLE_TEX, work_dir)
    assert pdf.name == "main.pdf"
    assert pdf.exists()
    assert pdf.stat().st_size > 0
    assert pdf.read_bytes().startswith(b"%PDF")


@pdflatex_available
def test_compile_handles_unicode_and_accents(compiler: LatexCompiler, work_dir: Path):
    tex = SIMPLE_TEX.replace("FastAPI", "FastAPI café, Zürich, naïve")
    pdf = compiler.compile(tex, work_dir)
    extracted = subprocess.run(
        ["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=False
    ).stdout
    assert "café" in extracted
    assert "Zürich" in extracted
    assert "naïve" in extracted


@pdflatex_available
def test_compile_failure_returns_latex_compilation_failed(
    compiler: LatexCompiler, work_dir: Path
):
    with pytest.raises(LatexCompilationFailed) as excinfo:
        compiler.compile(r"\begin{document} \thisisnotacommand{} \end{document}", work_dir)
    assert excinfo.value.code == "LATEX_COMPILATION_FAILED"
    assert excinfo.value.status_code == 502


def test_missing_output_even_on_success_returns_failure(
    monkeypatch: pytest.MonkeyPatch, work_dir: Path
):
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], returncode=0, stdout=b"", stderr=b""
        )
    )
    with pytest.raises(LatexCompilationFailed) as excinfo:
        LatexCompiler().compile(SIMPLE_TEX, work_dir)
    assert excinfo.value.code == "LATEX_COMPILATION_FAILED"


def test_empty_output_pdf_returns_failure(
    monkeypatch: pytest.MonkeyPatch, work_dir: Path
):
    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess:
        (work_dir / "main.pdf").write_bytes(b"")
        return subprocess.CompletedProcess(args[0], returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(LatexCompilationFailed) as excinfo:
        LatexCompiler().compile(SIMPLE_TEX, work_dir)
    assert excinfo.value.code == "LATEX_COMPILATION_FAILED"


def test_timeout_returns_latex_compilation_failed(
    monkeypatch: pytest.MonkeyPatch, work_dir: Path
):
    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout_run)
    with pytest.raises(LatexCompilationFailed) as excinfo:
        LatexCompiler(timeout=5.0).compile(SIMPLE_TEX, work_dir)
    assert excinfo.value.code == "LATEX_COMPILATION_FAILED"


def test_compile_never_uses_a_shell(monkeypatch: pytest.MonkeyPatch, work_dir: Path):
    seen: dict = {}

    def fake_run(*args, **kwargs):
        seen["args"] = args[0]
        seen["shell"] = kwargs.get("shell", False)
        (work_dir / "main.pdf").write_bytes(b"%PDF-1.4 fake")
        return subprocess.CompletedProcess(args[0], returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    LatexCompiler().compile(SIMPLE_TEX, work_dir)
    assert seen["shell"] is False
    assert "-no-shell-escape" in seen["args"]
    assert seen["args"][0] == "pdflatex"