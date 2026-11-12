# Decision 0113: gate directional dispositions on hypothesis testability

**Date:** 2026-11-12

**Status:** Implemented

## Context

The shared investigation contract checked that a declared disposition matched its evidence relationships. It separately retained each hypothesis's testability state, but did not require those fields to agree. A record could therefore label a hypothesis `NOT_TESTED` or `NOT_TESTABLE_WITH_RETAINED_EVIDENCE` while also declaring it `SUPPORTED_WITHIN_SCOPE` or `CONTRADICTED_WITHIN_SCOPE` from unanimous directional relationships.

## Decision

Reject a directional disposition when the same hypothesis is marked `NOT_TESTED` or `NOT_TESTABLE_WITH_RETAINED_EVIDENCE`. Permit `UNRESOLVED` or `NOT_EVALUATED` as appropriate. `DESCRIPTIVE_ONLY` and `DESCRIPTIVE_ASSOCIATION_ONLY` remain eligible for a scoped directional summary when their explicitly recorded relationships agree; this structural rule does not validate the scientific correctness of those relationships.

## Consequences and limits

- The reusable contract and draft validation now catch contradictions between a hypothesis's testability and disposition before the assessment is served or saved.
- Existing retained case assessments were scanned for the contradictory combination; none required correction.
- This is a consistency safeguard, not an automated source-suitability evaluator, causal test, or evidence-quality judgment.

## Verification

Focused regression cases cover both disallowed testability states and directional outcomes. The updated hypothesis validator was also applied to all 15 retained hypothesis sets under `data/cases` and `data/research`; none required a migration. The other retained-case contract checks remain in the full suite.

- Focused investigation, synthetic-scenario, case-record, and cross-sensor tests: **114 passed**.
- Full repository suite: `.venv/bin/python -m pytest -q` — **493 passed**.
- A broader contract scan validated 14 of 15 historical assessment records. The remaining November 7 snapshot fails a pre-existing follow-up-design requirement for F5; the failure occurs after hypothesis validation and is unrelated to this decision. The active T024 and T163 assessment records pass their contract tests.
