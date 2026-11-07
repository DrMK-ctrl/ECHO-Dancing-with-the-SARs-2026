# Decision 0021: Record explicit evidence relationships to hypotheses

**Date:** 2026-11-07  
**Status:** Implemented as a deterministic reasoning primitive; only the current diagnostic case is integrated

## Context

The first linked cross-sensor assessment retained evidence identifiers and hand-authored hypothesis states, but did not show how each source bears on each explanation. That made the assessment harder to challenge and left state assignment outside a tested rule. A QA-cleared NISAR temporal pair is still unavailable, so the reasoning contract should be testable independently of provider product status without presenting fixtures as observations.

## Decision

- Give every hypothesis/evidence relationship one explicit analyst-authored label: `SUPPORTS`, `CONTRADICTS`, `DOES_NOT_DISTINGUISH`, or `LIMITS_INTERPRETATION`, together with a rationale.
- Derive a deliberately conservative disposition: `SUPPORTED_WITHIN_SCOPE` or `CONTRADICTED_WITHIN_SCOPE` only when all recorded relationships point consistently in that direction; `UNRESOLVED` when evidence is nondiscriminating, limiting, mixed, or conflicting; `NOT_EVALUATED` when no relevant evidence is recorded.
- Reject duplicate or unknown evidence identifiers and empty rationales. Do not calculate a score, probability, or confidence.
- Keep this reasoning helper downstream of product suitability, provider QA, measurement validity, and provenance checks. It cannot promote a diagnostic measurement or validate a scientific claim.
- Test the generic disposition rules with synthetic software fixtures, clearly separate from any satellite observation. Keep source-specific extraction and relationship rationales in the assessment builder until another scientifically suitable case demonstrates a need for broader adapters.

## Consequences and limits

The assessment interface can now expose why a source supports, contradicts, limits, or does not distinguish an explanation. The evaluator makes state transitions inspectable and regression-testable, but it does not independently determine whether a relationship label is scientifically correct. That judgment remains tied to the cited source, stated scope, and analyst rationale. This is a reasoning primitive, not a completed Investigation Engine.
