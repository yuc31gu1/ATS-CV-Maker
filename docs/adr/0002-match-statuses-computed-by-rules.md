# 0002 Match statuses are computed by rules, not assigned by the LLM

We decided that STRONG_MATCH / PARTIAL_MATCH / TRANSFERABLE / NO_EVIDENCE are assigned by deterministic rules over a curated, checked-in Skill Catalog, and that the LLM's only role is extracting Job Requirements from the Job Description and optionally writing a one-line rationale. Skills present and substantiated in experience/projects → STRONG_MATCH; present in Skills only → PARTIAL_MATCH; absent but adjacent (catalog-marked) → TRANSFERABLE; otherwise NO_EVIDENCE.

We rejected LLM-assigned statuses because they are opaque, non-deterministic, and untestable, and rejected a hybrid escalation path because "no evidence → strong" must never be possible through any route. Computed statuses keep matching auditable and unit-testable without an LLM present.
