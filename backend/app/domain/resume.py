import datetime as dt
import re
from typing import Any

from pydantic import BaseModel, Field
from pydantic_core import core_schema

CURRENT_SCHEMA_VERSION = 1

_MONTH_YEAR_RE = re.compile(r"^(\d{4})-(\d{2})$")


class MonthYear(str):
    """A YYYY-MM date value object. Renders as e.g. 'May 2024'."""

    def __new__(cls, value: str) -> "MonthYear":  # noqa: PYI034
        parsed = cls._parse(value)
        return super().__new__(cls, parsed.strftime("%Y-%m"))

    @staticmethod
    def _parse(value: str) -> dt.date:
        if not isinstance(value, str):
            raise TypeError("MonthYear must be a string")
        match = _MONTH_YEAR_RE.fullmatch(value)
        if match is None:
            raise ValueError(f"invalid MonthYear {value!r}, expected YYYY-MM")
        year, month = int(match.group(1)), int(match.group(2))
        try:
            return dt.date(year, month, 1)
        except ValueError as exc:
            raise ValueError(f"invalid MonthYear {value!r}, expected YYYY-MM") from exc

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> "MonthYear":
            if isinstance(value, MonthYear):
                return value
            try:
                return cls(value)
            except (ValueError, TypeError) as exc:
                raise ValueError(str(exc)) from exc

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.to_string_ser_schema(),
        )

    @property
    def year(self) -> int:
        return self._parse(str(self)).year

    @property
    def month(self) -> int:
        return self._parse(str(self)).month

    def render(self) -> str:
        return self._parse(str(self)).strftime("%B %Y")


class PersonalInformation(BaseModel):
    full_name: str = Field(min_length=1)
    headline: str = ""
    email: str = Field(default="", pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = ""
    location: str = ""
    website: str = ""


class Experience(BaseModel):
    company: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str = ""
    start_date: MonthYear
    end_date: MonthYear | None = None
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    school: str = Field(min_length=1)
    degree: str = ""
    field: str = ""
    location: str = ""
    start_date: MonthYear
    end_date: MonthYear | None = None


class Project(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    url: str = ""
    technologies: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    name: str = Field(min_length=1)
    issuer: str = ""
    date: MonthYear
    url: str = ""


class Resume(BaseModel):
    """The canonical Master Resume: the single source of truth for evidence."""

    id: str | None = None
    schema_version: int = CURRENT_SCHEMA_VERSION
    personal_information: PersonalInformation
    summary: str = ""
    skills: dict[str, list[str]] = Field(default_factory=dict)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)


def evidence_ids(resume: Resume) -> dict[str, str]:
    """Deterministic, index-based evidence IDs for the resume, in content order.

    IDs follow the spec's pattern (`experience:12:bullet:3`, `project:2`) and are
    stable for identical content, powering claim traceability downstream.
    """
    ids: dict[str, str] = {}
    for index, exp in enumerate(resume.experience):
        ids[f"experience:{index}"] = f"{exp.title} at {exp.company}"
        for bullet_index, bullet in enumerate(exp.bullets):
            ids[f"experience:{index}:bullet:{bullet_index}"] = bullet
    for index, proj in enumerate(resume.projects):
        ids[f"project:{index}"] = proj.name
    for index, edu in enumerate(resume.education):
        ids[f"education:{index}"] = f"{edu.degree} at {edu.school}"
    for index, cert in enumerate(resume.certifications):
        ids[f"certification:{index}"] = cert.name
    return ids