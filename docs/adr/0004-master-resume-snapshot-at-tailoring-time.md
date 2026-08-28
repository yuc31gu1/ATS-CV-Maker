# 0004 Master Resume edited in place; immutable snapshot at tailoring time

We decided that the Master Resume is edited in place with no per-save versioning, and that an immutable ResumeVersion snapshot is captured when a tailoring job starts. Every Generated Resume pins to a ResumeVersion — never to the live Master Resume — so past tailored artifacts and their ATS Compatibility Analysis stay reproducible no matter how the master changes later.

We rejected full versioning on every save (the "current master" becomes ambiguous and create-flow edits create noise versions) and rejected pinning by revision counter (a master edit would silently change past claims). Snapshot-on-tailor gives reproducibility where it matters at minimal cost.
