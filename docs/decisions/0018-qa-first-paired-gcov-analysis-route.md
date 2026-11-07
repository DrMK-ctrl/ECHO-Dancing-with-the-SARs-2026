# Decision 0018: QA-first bounded paired GCOV analysis route

**Date:** 2026-11-07
**Status:** Backend and workspace integration implemented; live real-data comparison remains QA-held

## Context

ECHO has a bounded single-scene raster preview and a paired GCOV measurement function, but no request path connects two selected products to that analyzer. The currently sampled NISAR products fail provider identification checks. This should prevent pixel comparison without preventing the software path from being integrated and checked.

## Decision

- Add `POST /api/gcov-pair-analysis` to accept two allowlisted ASF NISAR GCOV catalog features, a bounded WGS84 area, frequency, and diagonal real-valued layer.
- Retrieve the canonical provider QA summary for both products before reading identification metadata or measurement arrays. If either disposition is not `PASS`, return both QA evidence records as `QA_HELD`, with no measurement or manifest and without opening product HDF5 arrays.
- Only after both provider summaries pass, read allowlisted identification fields and the selected GCOV layer plus mask, number-of-looks, and exception mask for each bounded AOI.
- Use `analyze_gcov_pair` as the final gate for product QA detail, compatible metadata, acquisition intervals, distinct NISAR orbits, exact sampled grid equality, common validity, and reproducible manifest construction.
- Return geolocated change pixels only for a gate-cleared descriptive measurement. Never classify an event or infer cause or confidence in this route.

## Evidence and limits

- Unit and local HTTP tests exercise the QA-held early return and synthetic passing path; the QA-held path proves metadata and raster readers are not called before QA passes.
- The workspace now submits the selected catalog pair and AOI, renders the QA-held source records without a change raster, and supports a geolocated result only for a measured response. Full record inspection and JSON export are connected.
- Live access to the real Nepal candidate returned `FAIL` for both provider summaries; the API returned `QA_HELD`, with no measurement or manifest.
- No selected real NISAR pair has passed provider QA and the route has not produced a real-data change field.
- Synthetic passing-path tests validate software behavior, not scientific validity, real-product compatibility, or event interpretation. The map display and pixel inspector still need in-browser acceptance against a real QA-PASS product pair.

## Consequences

This connects selected catalog observations, bounded product windows, provider QA, the existing QA- and grid-gated measurement function, and the geographic workspace. Current QA holds remain unchanged. The next gates are browser verification of the held state, then a real compatible QA-cleared pair for acceptance of the measurement map and pixel inspector.
