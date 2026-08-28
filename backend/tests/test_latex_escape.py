"""LatexEscapeService: every reserved character escapes; Unicode survives.

The acceptance criteria for T6 name the exact character set: ``& % $ # _ { }``
plus URLs, Unicode, accented characters, and long bullets (spec user story 23).
"""

import pytest

from app.latex.escape import LatexEscapeService


@pytest.fixture
def escape() -> LatexEscapeService:
    return LatexEscapeService()


def test_escapes_all_reserved_characters(escape: LatexEscapeService):
    assert escape.escape("& % $ # _ { }") == r"\& \% \$ \# \_ \{ \}"


def test_escapes_backslash_caret_and_tilde(escape: LatexEscapeService):
    escaped = escape.escape("a\\b^c~d")
    assert "\\textbackslash{}" in escaped
    assert "\\textasciicircum{}" in escaped
    assert "\\textasciitilde{}" in escaped


def test_escape_is_deterministic(escape: LatexEscapeService):
    text = "Built APIs with FastAPI & PostgreSQL; 40% faster & $100k saved #1"
    assert escape.escape(text) == escape.escape(text)


def test_escape_leaves_unicode_and_accents_untouched(escape: LatexEscapeService):
    text = "café, naïve, Zürich — résumé over 5 ünits"
    assert escape.escape(text) == text


def test_escape_handles_long_bullets(escape: LatexEscapeService):
    long_bullet = (
        "Led the migration of the ordering service from a monolith to "
        "event-driven microservices over eighteen months, cutting p95 latency "
        "from 900ms to 120ms and reducing infrastructure cost by 40% while "
        "keeping 99.9% uptime across three regions. " * 3
    )
    escaped = escape.escape(long_bullet)
    assert "\\%" in escaped
    assert long_bullet.replace("%", "\\%") == escaped


def test_escape_url_escapes_reserved_characters(escape: LatexEscapeService):
    url = "https://example.com/search?q=a&b=2#frag_x~y^z"
    escaped = escape.escape_url(url)
    assert "\\&" in escaped
    assert "\\#" in escaped
    assert "\\_" in escaped
    assert "\\textasciitilde{}" in escaped
    assert "\\^{}" in escaped


def test_escape_url_leaves_plain_urls_unchanged(escape: LatexEscapeService):
    url = "https://example.com/path"
    assert escape.escape_url(url) == url


def test_escape_and_escape_url_do_not_share_backslash_handling(
    escape: LatexEscapeService,
):
    # hyperref's \href argument cannot carry \textbackslash (TeX stack
    # overflow); the URL table must leave backslashes alone.
    url = r"https://example.com/{}"
    assert "\\textbackslash" not in escape.escape_url(url)
    assert escape.escape_url(url) == r"https://example.com/\{\}"