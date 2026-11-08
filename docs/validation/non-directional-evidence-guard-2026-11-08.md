# Shared investigation evidence-direction guard — 2026-11-08

## Result

The shared `validate_investigation_contract` now rejects directional hypothesis relationships when an evidence artifact declares a non-directional role or status. The shared predicate is also used by draft assessment, review, and revision paths, replacing a draft-local role list that could drift from the retained-case rule.

Covered non-directional categories include QA-held or maturity-held SAR pairs, diagnostic SAR measurements and analyses, provider-QA metadata, and catalog-discovery metadata. These records can still be linked as `DOES_NOT_DISTINGUISH` or `LIMITS_INTERPRETATION` and can inform a quality prerequisite or evidence search. They cannot by themselves support or contradict the physical explanation.

The guard does not blanket-block other data. A retained optical-context record can still support a descriptive observation within its stated scope; it remains explicitly not a validation of SAR measurements. The T024 and T163 assessment records were included in focused regression coverage.

## Implementation

- `echo.investigation` owns the common role/status sets and `is_non_directional_evidence` predicate.
- The shared investigation contract checks each analyst-authored relationship against its linked artifact's declared role and status.
- Draft creation, draft assessment, and restored review paths call the same predicate.
- Counterfactual relationship previews also reject a proposed directional label for a non-directional source; preview mode cannot bypass the contract.
- The rule is deterministic and depends only on explicit record metadata. It does not inspect provider identity or infer source quality.

## Verification

The initial focused run across investigation contract, integrated synthetic scenario, draft lifecycle, cross-sensor assessment, and case-record tests passed: **105 passed**. After adding the integrated QA-hold and HTTP counterfactual-preview regressions, the full repository suite passed: **371 passed**. Python compilation and `git diff --check` also passed. No scientific measurement or causal assessment was changed.
