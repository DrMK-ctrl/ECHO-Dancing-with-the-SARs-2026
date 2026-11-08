# Decision 0058: Start analyst-authored investigations from pair records

**Date:** 2026-11-08
**Status:** Pair-linked draft and single-hypothesis next-test workflow implemented; persistence and evidence retrieval remain open

## Context

The existing investigation contract supports product-independent evidence roles, explicit analyst-assigned relationships, falsifiable single-hypothesis follow-ups, and deterministic scoped dispositions. Its integrated case workflow is tied to retained cases, however, and a newly selected NISAR or OPERA pair could not enter that workflow through the interface.

## Decision

Allow a user to start an unassessed investigation draft from the exact pair-analysis record currently shown in the map workspace. The analyst supplies the investigation question, at least two distinct hypotheses, their scope and test conditions, and one planned next observation tied to exactly one hypothesis. The plan records expected, weakening, and inconclusive outcomes, acceptance gates, interpretation limits, and a rationale for pursuing the test.

The draft embeds the submitted pair record and stores its canonical JSON SHA-256. It retains the pair's original status, provider QA, maturity, and product identities. The checksum records submitted bytes; draft creation does not re-fetch or authenticate the provider record. Hypotheses remain `NOT_EVALUATED`, carry no evidence relationships, and the proposed follow-up remains `NOT_SEARCHED`. No ranking or inferred scientific relationship is produced.

Supported source roles distinguish descriptive NISAR GCOV measurements, QA-held and maturity-held NISAR pairs, diagnostic Sentinel-1-derived OPERA measurements, and OPERA pairs without common clear measurements. Synthetic fixture-only and unknown pair states are rejected.

## Consequences

- Investigation planning can progress from a real selected pair record without waiting for a QA-cleared NISAR pair.
- A QA-held or diagnostic record can be used to frame questions but cannot be presented as an accepted measurement or finding.
- The planned next observation is scoped to one authored hypothesis and must include explicit acceptance and inconclusive conditions.
- Drafts are currently downloadable records, not server-persisted investigations. Retrieving, validating, linking, and assessing follow-up evidence remains future work.
- A checksum alone does not authenticate the supplied record or establish source credibility.

## Verification

See [the investigation-draft workflow validation](../validation/investigation-draft-workflow-2026-11-08.md).
