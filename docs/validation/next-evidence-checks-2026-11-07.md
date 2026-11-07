# Next-evidence checks in the investigation workspace

**Validated:** 2026-11-07
**Scope:** Render case-review evidence gaps and gate-derived checks without analyzing or inventing scientific findings.

## Behavior

When a retained case review provides `next_evidence_gates`, the interface displays those source-authored checks and labels them **CASE REVIEW RECORD**. **VIEW SOURCE** opens the full local review JSON so users can inspect the context, evidence links, and limits behind the list.

For a catalog search without a review record, ECHO derives a short set of next checks from the current deterministic gate states and labels them **DERIVED FROM CURRENT GATES**. A QA-held pair receives a stop-before-comparison instruction; an unreviewed pair prompts QA retrieval; a pair without pixel analysis prompts grid and mask checks. These are workflow checks, not hypotheses, scientific conclusions, or AI outputs.

## Browser validation

Headless Firefox checked three local workspaces:

- Istanbul review: four next-evidence checks appeared; the case-review source inspector opened and contained `next_evidence_gates`.
- Mozambique QA review: three next-evidence checks appeared; the QA-review source inspector opened and contained its source record.
- A zero-observation catalog-only workspace: two checks were derived from current gates, with no case-review source button.

No SAR pixels, QA summaries, or external evidence were retrieved during this check. Existing provider QA statuses and candidate records were unchanged.

## Limits

The list does not evaluate whether a recommendation is scientifically correct, complete, or satisfied. It does not store analyst notes, revise a case assessment, or implement hypothesis scoring. Those capabilities require accepted real measurements and a validated evidence contract.
