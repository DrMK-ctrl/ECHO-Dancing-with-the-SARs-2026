# Decision 0024: Case-scoped investigation evidence

**Status:** Accepted
**Date:** 2026-11-08

## Context

The local server previously served one global DSWx-HLS record and one global cross-sensor assessment for every catalog case. Opening a different case could therefore pair its map or catalog with unrelated evidence. The Rio Grande do Sul T024 and T163 investigations need the same interface behavior while retaining distinct dates, SAR products, optical products, and assessments.

## Decision

Each investigation case may declare project-relative DSWx-HLS and cross-sensor assessment paths in a versioned `investigation.json` manifest beside its catalog. The server resolves those paths under the repository root, rejects paths that escape it, applies the existing response-size limits, and returns no evidence when the selected case does not declare it. The case review may also identify a preferred RTC-S1 pair; the live catalog selector uses it only when ASF returns that exact pair.

Cases remain launchable through the existing `--case-file` option. This preserves the current workspace and makes evidence selection explicit at the case boundary without introducing a separate case database or silently sharing evidence.

## Consequences

- T024 and T163 can be inspected in the same local UI without cross-case evidence leakage.
- The assessment retains links and checksums to its exact measurement, optical context, and catalog screen.
- An unconfigured case cannot accidentally receive the Rio Grande do Sul optical layer or assessment.
- The manifest does not validate the scientific correctness of the referenced records; record schemas, source checksums, product QA, and scientific suitability remain separate gates.
- Cases are selected when launching the server; an in-application case switcher is not implemented.
