from app import catalog


def test_canonical_of_resolves_synonyms():
    assert catalog.canonical_of("AWS") == "aws"
    assert catalog.canonical_of("Amazon Web Services") == "aws"
    assert catalog.canonical_of("postgres") == "postgresql"
    assert catalog.canonical_of("k8s") == "kubernetes"


def test_canonical_of_unknown_returns_none():
    assert catalog.canonical_of("Quantum Bicycling") is None


def test_fastapi_and_flask_are_related_not_synonyms():
    assert catalog.canonical_of("fastapi") != catalog.canonical_of("flask")
    assert catalog.is_related("fastapi", "flask")
    assert catalog.is_related("flask", "fastapi")


def test_unrelated_skills_are_not_related():
    assert not catalog.is_related("fastapi", "docker")
    assert not catalog.is_related("python", "kubernetes")


def test_skills_in_text_finds_synonyms_and_adjacent():
    found = catalog.skills_in_text("Experience with Amazon Web Services and FastAPI")
    assert "aws" in found
    assert "fastapi" in found


def test_skills_in_text_uses_word_boundaries():
    found = catalog.skills_in_text("JavaScript engines power the web")
    assert "javascript" in found
    assert "java" not in found


def test_skills_in_text_returns_deterministic_order():
    first = catalog.skills_in_text("Python and React and AWS")
    second = catalog.skills_in_text("AWS and React and Python")
    assert first == second == ["aws", "python", "react"]


def test_related_to_exposes_adjacent_technologies():
    related = catalog.related_to("fastapi")
    assert "flask" in related
    assert "django" in related