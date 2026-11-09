# Disclose source coverage for each hypothesis

## Decision

For each investigation hypothesis, show which source artifacts have a recorded relationship and which artifacts in the same investigation have no relationship recorded for that hypothesis. Keep the other artifacts unclassified, and link each one to the existing source inspector.

## Rationale

An investigation-level evidence list can contain records that are not linked to every explanation. Showing only linked evidence can make that gap hard to notice during review. The disclosure makes the coverage gap visible while preserving the analyst's responsibility to assess relevance.

The interface must state that an unlinked source has not been assessed for that hypothesis. It must not treat missing links as negative evidence, proof of irrelevance, or independent corroboration. If every currently listed artifact is linked, that only describes the current record; it does not establish that the source set is complete.

## Scope

This is a presentation change in the shared investigation renderer. It does not alter evidence records, assign relationships, change hypothesis dispositions, or make scientific claims. Browser interaction was exercised on the retained T163 case; it does not establish layout quality across viewports or generalized browser-driven case creation.

See [validation](../validation/investigation-hypothesis-source-coverage-2026-11-09.md).
