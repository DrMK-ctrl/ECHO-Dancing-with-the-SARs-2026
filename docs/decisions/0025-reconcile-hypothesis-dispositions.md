# Decision 0025: Reconcile hypothesis dispositions with evidence links

**Date:** 2026-11-08
**Status:** Implemented; validates record consistency, not scientific correctness

## Context

The assessment builder derives each hypothesis disposition from its analyst-authored evidence relationships. The reusable record validator previously checked that evidence identifiers matched, but did not check that a saved disposition still agreed with those relationships. The local interface also served saved assessments without validating that relationship. A stale or manually edited `SUPPORTED_WITHIN_SCOPE` state could therefore be displayed beside contradictory or limiting evidence.

## Decision

- Require a recognized disposition on every hypothesis record.
- Validate every evidence relationship and nonempty rationale, then recompute the deterministic disposition from those relationships.
- Reject a record when its declared disposition differs from the recomputed result.
- Apply the same validation when the local server loads a case assessment, so malformed saved records are not presented as valid investigations.
- Keep evidence relationships analyst-authored. This check confirms internal consistency only; it does not decide whether a measurement is valid or an interpretation is scientifically correct.

## Verification

- Synthetic tests cover stale dispositions, mixed support and contradiction, unsupported relationship labels, and missing rationales.
- The assessment endpoint rejects a stale record with HTTP 503 and serves a structurally consistent record.
- The full project suite passes. Rebuilding the retained T163 assessment preserves its unresolved causal interpretation and five provenance-linked evidence artifacts.
