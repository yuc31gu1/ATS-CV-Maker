# 0001 LLM never controls the document pipeline

We decided to keep the LLM strictly inside content roles (job requirement extraction, evidence-supported bullet rewriting) and never let it decide structure, layout, or output validity. The deterministic Tailoring Engine selects and orders evidence; a deterministic LaTeX renderer owns typography and section order; the PDF validator gates output. A claim-verification gate rejects any generated bullet whose technologies, numbers, or employers are not traceable to source evidence.

The alternative — an LLM-driven template generator producing "random LaTeX" — is explicitly what the product must not be. This boundary is what makes the pipeline auditable, testable, and safe (the LLM can never inject arbitrary LaTeX or fabricated claims).
