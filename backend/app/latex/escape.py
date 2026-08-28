"""LaTeX escaping for all untrusted user content (ADR-0001, spec PRD)."""


class LatexEscapeService:
    """Escapes user content before insertion into the LaTeX template.

    User content (name, bullets, skills, URLs, dates) is never trusted: every
    reserved character is replaced with its LaTeX-safe form so special
    characters can never break compilation (spec user story 23). URLs get a
    separate table because hyperref's ``\\href`` argument cannot carry a
    ``\\textbackslash`` without overflowing TeX's input stack.
    """

    _BACKSLASH_PLACEHOLDER = "\x00"

    _TEXT_REPLACEMENTS = (
        ("{", r"\{"),
        ("}", r"\}"),
        ("$", r"\$"),
        ("&", r"\&"),
        ("#", r"\#"),
        ("^", r"\textasciicircum{}"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("~", r"\textasciitilde{}"),
    )

    _URL_REPLACEMENTS = (
        ("{", r"\{"),
        ("}", r"\}"),
        ("$", r"\$"),
        ("&", r"\&"),
        ("#", r"\#"),
        ("^", r"\^{}"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("~", r"\textasciitilde{}"),
    )

    def escape(self, text: str) -> str:
        """Escape text content for a LaTeX body position."""
        protected = text.replace("\\", self._BACKSLASH_PLACEHOLDER)
        for char, escaped in self._TEXT_REPLACEMENTS:
            protected = protected.replace(char, escaped)
        return protected.replace(self._BACKSLASH_PLACEHOLDER, r"\textbackslash{}")

    def escape_url(self, url: str) -> str:
        """Escape a URL for the argument of ``\\href``."""
        result = url
        for char, escaped in self._URL_REPLACEMENTS:
            result = result.replace(char, escaped)
        return result