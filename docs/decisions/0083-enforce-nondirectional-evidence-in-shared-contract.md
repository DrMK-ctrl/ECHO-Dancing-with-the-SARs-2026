# Decision 0083: enforce non-directional evidence roles in the shared contract

Date: 2026-11-08

## Context

Analyst-authored drafts already reject `SUPPORTS` and `CONTRADICTS` for explicitly diagnostic SAR, QA-held, and catalog-only evidence. The shared case-investigation validator checked identifiers, relationships, testability states, and follow-up contracts, but did not apply the same role/status boundary. A retained or newly built assessment could therefore pass the shared contract with a directional physical explanation based only on a QA hold or catalog metadata.

## Decision

Centralize a small set of explicitly non-directional evidence roles and statuses in `echo.investigation`. Apply the guard in the shared investigation contract and reuse the same predicate in draft assessment, review, and revision paths. Reject only directional relations (`SUPPORTS`, `CONTRADICTS`) for those explicit categories. Continue to permit non-directional labels (`DOES_NOT_DISTINGUISH`, `LIMITS_INTERPRETATION`). Other evidence roles are unaffected; for example, optical context can support a specifically scoped descriptive observation when the record says so.

## Boundaries

This is a consistency safeguard, not an automated source-quality assessment. It does not decide whether an analyst-authored relationship is scientifically true, infer a role from a provider name, or decide whether other evidence is suitable. A QA record may be relevant to a quality-gate follow-up; it does not establish the physical mechanism being investigated.

## Verification

Tests reject both support and contradiction relations for QA-held, provider-QA metadata, and catalog-only artifacts, preserve nondirectional handling, and confirm that suitable optical context is not blanket-blocked. Retained T024 and T163 assessment records continue through the shared validator. See [validation](../validation/non-directional-evidence-guard-2026-11-08.md).
