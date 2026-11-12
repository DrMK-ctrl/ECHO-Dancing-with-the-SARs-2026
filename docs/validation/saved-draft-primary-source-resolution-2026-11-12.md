# Saved-draft primary SAR source resolution — 2026-11-12

## Defect and correction

The saved-draft adversarial challenge selected `evidence_artifacts[0]` as the observation. Drafts may contain staged context records, and their artifact list may be reordered while remaining valid. In that case the challenge could describe a non-SAR source as the primary observation.

ECHO now resolves the unique primary SAR artifact by its declared role, using one shared role set for draft validation, challenge assembly, follow-up screening, and validated case-source lineage. Evidence list order no longer determines which observation is challenged.

## Verification

- A regression first failed with a valid reversed draft: the report identified `USER-SOURCE-…` instead of the linked `SAR-PAIR-…` observation.
- After the correction, the direct challenge builder returns the SAR record, preserves the staged context as unassessed evidence, and retains the SAR provider-QA hold.
- The saved-draft HTTP workflow now exercises the same reversed-artifact case and confirms the returned challenge still names the exact primary SAR evidence ID.
- Focused investigation-draft, adversarial, and web suites: **106 passed**.

This change corrects evidence labeling and lineage selection. It does not alter measurements, provider QA, evidence relationships, or scientific conclusions.
