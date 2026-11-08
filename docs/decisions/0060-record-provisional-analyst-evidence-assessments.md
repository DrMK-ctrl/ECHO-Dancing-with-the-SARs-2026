# Decision 0060: Record provisional analyst evidence assessments

**Date:** 2026-11-08
**Status:** Implemented for exported investigation drafts; source suitability validation and durable storage remain open

## Context

Pair-linked drafts could define competing hypotheses and stage source records, but could not connect an inspected source to a hypothesis. The shared investigation contract already had deterministic rules for summarizing explicit relationships. Extending those rules into draft editing must not imply that ECHO authenticated the reviewer, validated a source, or established a scientific finding.

## Decision

Allow an unauthenticated local user to record one or more explicit source-to-hypothesis relationships with an analyst-declared fit for the stated scope, rationale, inspected record basis, and interpretation limits. Directional relationships require `SUITABLE_FOR_STATED_SCOPE`; this is a user declaration, not source validation. Preserve the source record and its checksum. Record an assessment timestamp, each referenced source checksum, and a checksum of the assessment ledger. Derive the hypothesis disposition through the existing deterministic relationship rule without scores or probabilities.

The resulting state is `DRAFT_ANALYST_ASSESSED_UNVERIFIED`. Source provider QA, user-supplied status, review state, independence, and product maturity remain unchanged. The interface labels the result provisional and exposes the analyst's review basis and limitations beside the linked source. It does not offer analyst challenge controls that require a persisted case assessment.

QA-held, product-maturity-held, descriptive-only NISAR, diagnostic OPERA, and no-common-valid-pixel SAR records may be assigned only `DOES_NOT_DISTINGUISH` or `LIMITS_INTERPRETATION`. They cannot be coded as directional support or contradiction. The assessment stays in a downloadable draft; it is not written to the case store or presented as an accepted scientific result.

## Consequences

- Analysts can make competing explanations evidence-linked and inspect the basis of each relationship.
- Relationships remain human-authored. The deterministic disposition is a summary of their labels, not a confidence estimate or independent scientific evaluation.
- Assessment checksums detect ordinary mismatches between the ledger and its linked records; they are not signatures and do not authenticate authorship.
- Analyst-declared source fit does not prove temporal or spatial suitability, provider authenticity, scientific quality, or source independence; source-specific validation still needs to precede a validated finding.
- Persistence, revision history across sessions, and reopening a draft for additional source retrieval remain future work.

## Verification

See [the analyst assessment validation record](../validation/investigation-analyst-assessment-2026-11-08.md).
