from pydantic import BaseModel, Field


class ATSAnalysis(BaseModel):
    """Measured ATS Compatibility Analysis for one generated PDF.

    Reports measured checks only — never a pass/fail "ATS score" (user story
    26). Required/preferred keyword coverage and evidence coverage are
    computed over high-priority requirements; requirements the Skill Catalog
    cannot measure are listed explicitly in ``unsupported_requirements``. The
    page count is reported honestly, never auto-fitted (user story 33).
    """

    required_keyword_coverage: float | None = None
    preferred_keyword_coverage: float | None = None
    evidence_coverage: float | None = None
    pdf_text_extraction: bool
    single_column: bool
    standard_headings: bool
    critical_info_in_body: bool
    unexpected_tables: int = 0
    unexpected_graphics: int = 0
    page_count: int
    warnings: list[str] = Field(default_factory=list)
    unsupported_requirements: list[str] = Field(default_factory=list)