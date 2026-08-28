import re
from collections.abc import Sequence

from pydantic import BaseModel

from app.domain.analysis import (
    Importance,
    JobRequirement,
    LLMJobAnalysis,
    RequirementCategory,
)
from app.llm.base import JD_END_MARKER, JD_START_MARKER

_SENIORITY_RE = re.compile(r"(\d+\+?\s*years?|years? of experience|experience level)")


class FixtureLLMProvider:
    """Deterministic in-process LLM provider for tests and demo mode.

    Either replays a scripted sequence of responses (for retry/validation
    tests) or runs a small keyword-based analyzer over the Job Description
    embedded in the prompt, so the whole pipeline runs without an LLM key.
    """

    _SENIORITY_LEVELS = ("principal", "staff", "lead", "senior", "mid", "junior")
    _PREFERRED_MARKERS = ("preferred", "nice to have", "nice-to-have", "a plus", "bonus")
    _RESPONSIBILITY_MARKERS = ("responsib", "you will", "you'll", "you would", "duties", "day-to-day")
    _SOFT_SKILL_WORDS = (
        "communication",
        "teamwork",
        "collaboration",
        "leadership",
        "problem-solving",
        "problem solving",
        "adaptability",
        "ownership",
        "mentorship",
        "attention to detail",
        "interpersonal",
    )
    _DOMAIN_WORDS = (
        "finance",
        "healthcare",
        "e-commerce",
        "ecommerce",
        "saas",
        "fintech",
        "cloud",
        "data",
        "machine learning",
        "security",
        "devops",
    )
    _HIGH_MARKERS = ("must", "required", "essential", "mandatory", "minimum")
    _LOW_MARKERS = ("preferred", "nice to have", "nice-to-have", "a plus", "bonus", "familiarity")

    def __init__(self, responses: Sequence[BaseModel | dict] | None = None) -> None:
        self._responses = list(responses) if responses is not None else None

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        if self._responses is not None:
            if not self._responses:
                raise AssertionError("FixtureLLMProvider exhausted its scripted responses")
            return self._responses.pop(0)
        return self.analyze_jd(self._jd_from_prompt(prompt))

    @staticmethod
    def _jd_from_prompt(prompt: str) -> str:
        start = prompt.find(JD_START_MARKER)
        end = prompt.find(JD_END_MARKER)
        if start == -1 or end == -1 or end <= start:
            return ""
        return prompt[start + len(JD_START_MARKER) : end].strip()

    def analyze_jd(self, jd_text: str) -> LLMJobAnalysis:
        lines = [line.strip() for line in jd_text.splitlines() if line.strip()]
        prose = [line for line in lines if not self._is_section_header(line)]
        return LLMJobAnalysis(
            role=self._extract_role(prose),
            seniority=self._extract_seniority(
                " ".join(line for line in prose if not self._is_requirement_line(line)).lower()
            ),
            requirements=self._extract_requirements(lines),
        )

    def _extract_requirements(self, lines: list[str]) -> list[JobRequirement]:
        section: str | None = None
        requirements: list[JobRequirement] = []
        for line in lines:
            if self._is_section_header(line):
                section = self._section_name(line)
                continue
            if self._is_requirement_line(line):
                requirements.append(self._classify(line, section))
        return requirements

    def _classify(self, line: str, section: str | None) -> JobRequirement:
        text = re.sub(r"^[-*•]\s*|\d+[.)]\s*", "", line).strip()
        lower = text.lower()
        if section == "responsibilities":
            category = RequirementCategory.RESPONSIBILITY
        elif section == "requirements":
            category = self._category_requirement(lower)
        else:
            category = self._category_general(lower)
        return JobRequirement(
            requirement=text,
            category=category,
            importance=self._importance(lower),
            context=text,
        )

    def _category_requirement(self, lower: str) -> RequirementCategory:
        if any(word in lower for word in self._SOFT_SKILL_WORDS):
            return RequirementCategory.SOFT_SKILL
        if any(word in lower for word in self._DOMAIN_WORDS):
            return RequirementCategory.DOMAIN
        if any(marker in lower for marker in self._PREFERRED_MARKERS):
            return RequirementCategory.PREFERRED
        if _SENIORITY_RE.search(lower):
            return RequirementCategory.SENIORITY
        return RequirementCategory.REQUIRED

    def _category_general(self, lower: str) -> RequirementCategory:
        if any(marker in lower for marker in self._RESPONSIBILITY_MARKERS):
            return RequirementCategory.RESPONSIBILITY
        if any(word in lower for word in self._SOFT_SKILL_WORDS):
            return RequirementCategory.SOFT_SKILL
        if any(word in lower for word in self._DOMAIN_WORDS):
            return RequirementCategory.DOMAIN
        if any(marker in lower for marker in self._PREFERRED_MARKERS):
            return RequirementCategory.PREFERRED
        if _SENIORITY_RE.search(lower):
            return RequirementCategory.SENIORITY
        return RequirementCategory.REQUIRED

    def _importance(self, lower: str) -> Importance:
        if any(marker in lower for marker in self._HIGH_MARKERS):
            return Importance.HIGH
        if any(marker in lower for marker in self._LOW_MARKERS):
            return Importance.LOW
        return Importance.MEDIUM

    @staticmethod
    def _is_requirement_line(line: str) -> bool:
        return line.startswith(("-", "*", "•")) or bool(re.match(r"^\d+[.)]", line))

    @staticmethod
    def _is_section_header(line: str) -> bool:
        return line.endswith(":") and not bool(re.match(r"^(role|title|position)\s*[:：]", line, re.IGNORECASE))

    @staticmethod
    def _section_name(line: str) -> str | None:
        name = line[:-1].strip().lower()
        if any(key in name for key in ("responsib", "dut", "you will", "you'll")):
            return "responsibilities"
        if any(key in name for key in ("requirement", "qualification", "skill", "what we look")):
            return "requirements"
        return None

    @staticmethod
    def _extract_role(lines: list[str]) -> str:
        for line in lines:
            match = re.match(r"^(role|title|position)\s*[:：]\s*(.+)$", line, re.IGNORECASE)
            if match:
                return match.group(2).strip()
        if lines and len(lines[0]) <= 80:
            return lines[0]
        return "Unknown role"

    def _extract_seniority(self, text_lower: str) -> str | None:
        for level in self._SENIORITY_LEVELS:
            if re.search(rf"\b{level}\b", text_lower):
                return level.capitalize()
        return None