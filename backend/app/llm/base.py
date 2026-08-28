from typing import Protocol, runtime_checkable

from pydantic import BaseModel

JD_START_MARKER = "<JobDescription>"
JD_END_MARKER = "</JobDescription>"

TAILOR_SCOPE_START_MARKER = "<TailorScope>"
TAILOR_SCOPE_END_MARKER = "</TailorScope>"


@runtime_checkable
class LLMProvider(Protocol):
    """LLM abstraction with structured output support (ADR-0001, spec PRD)."""

    def generate_structured(
        self, *, prompt: str, output_schema: type[BaseModel]
    ) -> BaseModel: ...