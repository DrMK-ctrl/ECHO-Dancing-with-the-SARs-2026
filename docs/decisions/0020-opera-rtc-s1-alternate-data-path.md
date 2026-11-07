# Decision 0020: Separate OPERA RTC-S1 alternate data path

**Date:** 2026-11-07  
**Status:** Bounded API, map interface, and one live diagnostic pair verified; product QA and event interpretation remain open

## Context

The available VALIDATED NISAR GCOV temporal candidate remains held by its provider QA `FAIL`. ECHO already has a bounded OPERA RTC-S1 COG reader and a product-specific masked log-ratio routine. OPERA RTC-S1 is derived from Sentinel-1 and must remain explicitly distinct from NISAR observations.

## Decision

- Add a bounded ASF OPERA RTC-S1 catalog query using the selected WGS84 rectangle and date range. Preserve returned provider features and screen repeated burst, platform, spacing, and product-version identities as metadata candidates only.
- Add a separate pair API that reads the two selected RTC-S1 polarization assets and provider masks for the same bounded AOI, then applies the existing strict grid, acquisition, mask, and pixel-center compatibility checks.
- Preserve the analyzer's `provider_qa.status=NOT_RETRIEVED` and diagnostic disposition. A successful raster calculation is not promoted to a provider-validated or event-level finding.
- Keep NISAR GCOV discovery and QA gates unchanged. OPERA is an alternate NASA-supported validation path, not a substitute or correction for NISAR QA evidence.

## Verification and limits

- Pure catalog tests cover WGS84/date validation, pair grouping, incompatibility separation, candidate-only labels, and result-cap disclosure.
- Pipeline tests check bounded AOI/polarization forwarding and reject duplicate products before raster reads.
- HTTP tests cover the OPERA catalog and pair endpoints, payload validation, and explicit source/QA labeling.
- Earthdata Login authenticated with the configured local netrc; an ASF asset range request returned HTTP 206 after redirects through Cumulus and Earthdata OAuth, with no EULA error.
- A live T024-050660-IW1 Sentinel-1A pair, 2024-05-11 and 2024-06-04, was read from ASF and processed over a 0.01° WGS84 AOI. Both products had identical EPSG:32722 grids and 1,199 common clear pixel centers. The calculation is retained as `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`; provider QA remains `NOT_RETRIEVED`.
- Firefox displayed the retained live catalog candidates, then called the live bounded pair endpoint, which fetched and processed the two ASF products. The map, source inspection, QA label, modal dismissal, and return to NISAR were verified without browser errors. The screenshot is in `docs/validation/opera-rtc-live-map-2026-11-07.png`.
- The project regression suite passed: 171 tests. Compile checks and `git diff --check` passed.
- This work does not change NISAR discovery, QA requirements, or scientific disposition. OPERA remains a distinct Sentinel-1-derived corroboration path, not a substitute for NISAR or independent event validation.
