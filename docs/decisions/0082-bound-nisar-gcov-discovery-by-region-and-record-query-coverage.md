# Decision 0082: bound NISAR GCOV discovery by region and report query coverage

Date: 2026-11-08

## Context

The PROVISIONAL GCOV catalog spans a wide date range, and a multi-day global query can reach ASF's 2,000-result cap before providing complete temporal coverage. Treating a capped or failed request like a complete empty search would produce misleading coverage conclusions. Repeating global searches also spends time on scenes irrelevant to a particular AOI.

## Decision

Keep the existing maturity-aware ASF search and metadata pair matcher. Allow an optional validated WGS84 bounding box and bounded multi-day date window. Record query execution separately from coverage, and label any capped or failed interval as incomplete. A spatial result is discovery metadata only; product QA, AOI pixel coverage, grid alignment, valid-pixel overlap, and scientific suitability remain separate gates.

## Evidence

The 2026-10-07 through 2026-10-23 global PROVISIONAL query returned 2,000 results and reached the cap, with only 2026-10-20 and 2026-10-21 present in that returned subset. It cannot establish absence of earlier scenes or pairs. A bounded WGS84 query around 41.15–41.27 E, 36.66–36.78 N returned five PROVISIONAL products over 2026-10-08, 2026-10-15, and 2026-10-20; two were 12-day metadata matches. QA reports for all four products in those two pairs have an aggregate provider identification-group `FAIL`. The same AOI had zero returned VALIDATED scenes in the completed 2026-10-21 through 2026-11-08 search. These results do not imply that no globally suitable VALIDATED pair exists.

## Consequences

Catalog records now distinguish global and spatial screens and retain query execution, coverage, per-window pagination, failed windows, caps, maturity, and spatial bounds. QA-held candidates are retained as diagnostics, not accepted comparison inputs. The bounded search result and exact QA reports are retained in [`provisional-gcov-coverage-and-qa-2026-11-08.md`](../validation/provisional-gcov-coverage-and-qa-2026-11-08.md).
