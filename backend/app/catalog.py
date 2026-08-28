"""Curated, checked-in Skill Catalog (ADR-0002).

The controlled semantic layer for matching. Resolves synonyms (`AWS` =
`Amazon Web Services`) within the catalog and marks distinct-but-adjacent
technologies (`FastAPI` vs `Flask`) as related — never as synonyms, so no
false equivalence is ever assumed. Matching statuses are computed by rules
over this catalog; the LLM never assigns them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WS_RE = re.compile(r"\s+")


def normalize(name: str) -> str:
    """Lowercase and collapse whitespace for catalog lookups."""
    return _WS_RE.sub(" ", name.strip().lower())


@dataclass(frozen=True)
class Skill:
    """A canonical skill with its synonyms and adjacent (related) technologies."""

    canonical: str
    aliases: tuple[str, ...] = ()
    related: tuple[str, ...] = ()


SKILLS: tuple[Skill, ...] = (
    Skill("python", aliases=("py", "python3", "python 3")),
    Skill("fastapi", related=("flask", "django")),
    Skill("flask", related=("fastapi", "django")),
    Skill("django", related=("fastapi", "flask")),
    Skill("aws", aliases=("amazon web services", "amazon webservices", "aws cloud")),
    Skill("amazon s3", aliases=("s3", "aws s3", "simple storage service")),
    Skill("amazon ec2", aliases=("ec2", "aws ec2")),
    Skill("docker", aliases=("containerization",)),
    Skill("kubernetes", aliases=("k8s",)),
    Skill("postgresql", aliases=("postgres", "psql", "postgres sql")),
    Skill("sql", related=("postgresql", "mysql")),
    Skill("mysql", related=("sql", "postgresql")),
    Skill("redis"),
    Skill("mongodb", aliases=("mongo db", "mongo")),
    Skill("react", aliases=("react.js", "reactjs", "react js")),
    Skill("typescript", aliases=("ts",)),
    Skill("javascript", aliases=("js",)),
    Skill("node.js", aliases=("node", "nodejs")),
    Skill("graphql"),
    Skill("rest api", aliases=("rest", "restful", "restful api")),
    Skill("ci/cd", aliases=("cicd", "continuous integration", "continuous delivery")),
    Skill("git", aliases=("github",)),
    Skill("terraform"),
    Skill("golang", aliases=("go",)),
    Skill("rust"),
    Skill("java"),
    Skill("sqlalchemy", related=("django",)),
    Skill("kafka", related=("rabbitmq",)),
    Skill("rabbitmq", related=("kafka",)),
    Skill("celery", related=("kafka", "rabbitmq")),
    Skill("machine learning", aliases=("ml",)),
    Skill("pandas"),
    Skill("numpy"),
    Skill("tensorflow"),
    Skill("pytorch"),
    Skill("html"),
    Skill("css"),
    Skill("tailwind", aliases=("tailwind css",)),
    Skill("nginx"),
    Skill("linux", aliases=("unix",)),
    Skill("latex"),
    Skill("next.js", aliases=("next", "nextjs")),
)

_CANONICAL_BY_NAME: dict[str, str] = {
    normalize(name): skill.canonical
    for skill in SKILLS
    for name in (skill.canonical, *skill.aliases)
}

_RELATED_BY_CANONICAL: dict[str, frozenset[str]] = {
    _skill.canonical: frozenset(_skill.related) for _skill in SKILLS
}


def canonical_of(name: str) -> str | None:
    """Return the canonical skill for a name or alias, or None if unknown."""
    return _CANONICAL_BY_NAME.get(normalize(name))


def related_to(canonical: str) -> frozenset[str]:
    """Canonical skills marked adjacent-but-distinct to a canonical skill."""
    return _RELATED_BY_CANONICAL.get(canonical, frozenset())


def synonyms_of(canonical: str) -> tuple[str, ...]:
    """All surface names (canonical + aliases) for a canonical skill.

    Used by deterministic rewrites to align wording with the Job Description's
    terminology while keeping every claim traceable to the same canonical.
    """
    for skill in SKILLS:
        if skill.canonical == canonical:
            return (skill.canonical, *skill.aliases)
    return ()


def is_related(a: str, b: str) -> bool:
    """True when two skills are adjacent-but-distinct (never synonyms)."""
    canonical_a = canonical_of(a)
    canonical_b = canonical_of(b)
    return (
        canonical_a is not None
        and canonical_b is not None
        and canonical_a != canonical_b
        and canonical_b in related_to(canonical_a)
    )


def skills_in_text(text: str) -> list[str]:
    """Canonical skills mentioned in text, matched on word boundaries.

    Returns canonicals in deterministic sorted order.
    """
    normalized = normalize(text)
    found: set[str] = set()
    for name, canonical in _CANONICAL_BY_NAME.items():
        if re.search(rf"\b{re.escape(name)}\b", normalized):
            found.add(canonical)
    return sorted(found)