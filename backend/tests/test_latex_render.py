"""LatexRenderingService: deterministic .tex owning layout, not content."""

from datetime import UTC, datetime

import pytest

from app.domain.resume import (
    Certification,
    Education,
    Experience,
    MonthYear,
    PersonalInformation,
    Project,
)
from app.domain.tailoring import TailoredResume
from app.latex.render import PREAMBLE, LatexRenderingService


def _tailored(**overrides) -> TailoredResume:
    kwargs = {
        "job_description_id": "jd-1",
        "resume_version_id": "rv-1",
        "resume_id": "r-1",
        "personal_information": PersonalInformation(
            full_name="Ada Lovelace",
            headline="Backend Engineer",
            email="ada@example.com",
            phone="+1 555",
            location="London",
            website="https://example.com",
        ),
        "summary": "Built API platforms with FastAPI & PostgreSQL.",
        "skills": {"Languages": ["Python", "SQL"], "Frameworks": ["FastAPI"]},
        "experience": [
            Experience(
                company="Acme",
                title="Engineer",
                location="London",
                start_date=MonthYear("2021-03"),
                end_date=MonthYear("2024-06"),
                bullets=["Built the ordering API with FastAPI."],
            )
        ],
        "education": [
            Education(
                school="University of London",
                degree="BSc Computer Science",
                start_date=MonthYear("2016-09"),
                end_date=MonthYear("2020-06"),
            )
        ],
        "projects": [
            Project(
                name="Ordering Platform",
                url="https://github.com/a/b",
                description="Scaled checkout to 1M orders.",
                bullets=["Cut checkout time by 40%."],
            )
        ],
        "certifications": [
            Certification(
                name="AWS Certified Developer",
                issuer="Amazon Web Services",
                date=MonthYear("2024-05"),
                url="https://example.com/cert",
            )
        ],
        "created_at": datetime.now(UTC),
    }
    kwargs.update(overrides)
    return TailoredResume(**kwargs)


@pytest.fixture
def renderer() -> LatexRenderingService:
    return LatexRenderingService()


def test_render_is_deterministic(renderer: LatexRenderingService):
    tailored = _tailored()
    assert renderer.render(tailored) == renderer.render(tailored)


def test_template_owns_typography_and_margins(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    for fragment in (
        r"\documentclass[10pt]{article}",
        r"\usepackage[letterpaper,margin=0.7in]{geometry}",
        r"\usepackage{lmodern}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\input glyphtounicode",
        r"\pdfgentounicode=1",
    ):
        assert fragment in tex


def test_template_owns_section_order(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    order = [
        tex.index(r"\section*{Summary}"),
        tex.index(r"\section*{Skills}"),
        tex.index(r"\section*{Experience}"),
        tex.index(r"\section*{Projects}"),
        tex.index(r"\section*{Education}"),
        tex.index(r"\section*{Certifications}"),
    ]
    assert order == sorted(order)


def test_contact_information_sits_in_the_document_body(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    assert "ada@example.com" in tex
    assert "+1 555" in tex
    assert "London" in tex
    assert r"\href{https://example.com}{https://example.com}" in tex


def test_bullets_render_through_itemize(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    assert r"\begin{itemize}" in tex
    assert r"\item Built the ordering API with FastAPI." in tex
    assert r"\end{itemize}" in tex


def test_dates_render_as_month_year(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    assert "March 2021 -- June 2024" in tex
    assert "September 2016 -- June 2020" in tex
    assert "May 2024" in tex


def test_ongoing_role_renders_present(renderer: LatexRenderingService):
    tailored = _tailored()
    tailored.experience[0].end_date = None
    tex = renderer.render(tailored)
    assert "March 2021 -- Present" in tex


def test_hyperlinks_render_as_href(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    assert r"\href{https://github.com/a/b}{https://github.com/a/b}" in tex
    assert r"\href{https://example.com/cert}{https://example.com/cert}" in tex


def test_user_content_is_escaped(renderer: LatexRenderingService):
    tailored = _tailored(summary="FastAPI & PostgreSQL; 40% faster, $2M saved #1")
    tex = renderer.render(tailored)
    assert "FastAPI \\& PostgreSQL; 40\\% faster, \\$2M saved \\#1" in tex


def test_empty_sections_are_omitted(renderer: LatexRenderingService):
    tailored = _tailored(projects=[], certifications=[], summary="")
    tex = renderer.render(tailored)
    assert r"\section*{Projects}" not in tex
    assert r"\section*{Certifications}" not in tex
    assert r"\section*{Summary}" not in tex
    assert r"\section*{Experience}" in tex


def test_template_renders_a_complete_document(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    assert tex.startswith(PREAMBLE)
    assert tex.rstrip().endswith(r"\end{document}")


def test_skills_render_by_category(renderer: LatexRenderingService):
    tex = renderer.render(_tailored())
    assert r"\textbf{Languages} Python, SQL" in tex
    assert r"\textbf{Frameworks} FastAPI" in tex