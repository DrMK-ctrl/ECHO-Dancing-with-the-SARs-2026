# Decision 0020: Separate OPERA RTC-S1 alternate data path

**Date:** 2026-11-07  
**Status:** Catalog and bounded pair API implemented; interface and live-raster acceptance remain open

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
- No live OPERA raster was read through this integration. ASF access previously reached an explicit EULA acceptance failure after successful Earthdata authentication. The pair API must not be presented as live-validated until access succeeds and a real compatible pair is processed.
- The current browser interface does not yet expose this path; that remains the next integration step.
