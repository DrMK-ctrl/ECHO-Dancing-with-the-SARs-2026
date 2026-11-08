# Surface recorded evidence dependencies within each hypothesis

**Status:** Implemented as a display-only analysis
**Date:** 2026-11-08

## Context

An investigation may cite multiple records under one explanation even when those records reuse the same source acquisitions, derive from one another, or use a shared recorded input. A separate lineage list makes those dependencies inspectable, but a reviewer comparing evidence under a hypothesis can overlook them.

## Decision

For each hypothesis, compare its cited evidence artifacts and surface explicit lineage links: shared source observations, a derivation relationship, or a common recorded derivation input. Keep the warning collapsible and link both artifacts to the existing source inspector. Do not infer an unrecorded dependency, change evidence relationships, combine evidence, or alter the hypothesis disposition.

The interface must say that missing lineage metadata does not prove independence. The resulting warning is a deterministic disclosure of the retained lineage graph, not a statistical independence test or scientific validation.

## Verification

The active T024 Firefox walkthrough displays the pair/series shared-acquisition warning under the water hypothesis. A rendered fixture also checks a cited source/derived pair and two records with a common recorded input. The full test suite and application compilation are run with this change.
