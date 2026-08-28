"""pdflatex compilation in an isolated temporary directory."""

import subprocess
from pathlib import Path

from app.errors import LatexCompilationFailed


class LatexCompiler:
    """Compiles ``.tex`` source with pdflatex via a subprocess argument array.

    Never a shell: user content can never reach a shell command (spec user
    story 24). Runs inside an isolated working directory with a timeout and
    no shell escape. Any failure (nonzero exit, timeout, missing or empty
    output PDF) surfaces as LATEX_COMPILATION_FAILED.
    """

    def __init__(self, *, executable: str = "pdflatex", timeout: float = 30.0) -> None:
        self._executable = executable
        self._timeout = timeout

    def compile(self, tex: str, work_dir: Path) -> Path:
        main_tex = work_dir / "main.tex"
        main_tex.write_text(tex, encoding="utf-8")
        args = [
            self._executable,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-no-shell-escape",
            main_tex.name,
        ]
        try:
            proc = subprocess.run(
                args,
                cwd=work_dir,
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LatexCompilationFailed(
                "pdflatex timed out",
                details={"timeout_seconds": self._timeout},
            ) from exc

        pdf = work_dir / "main.pdf"
        if proc.returncode != 0:
            raise LatexCompilationFailed(
                "pdflatex failed to compile the LaTeX source",
                details={"exit_code": proc.returncode},
            )
        if not pdf.exists() or pdf.stat().st_size == 0:
            raise LatexCompilationFailed(
                "pdflatex reported success but produced no PDF",
                details={"output": "missing"},
            )
        return pdf