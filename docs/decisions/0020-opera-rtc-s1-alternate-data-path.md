# Decision 0020: Separate OPERA RTC-S1 alternate data path

**Date:** 2026-11-07  
**Status:** Bounded API and one live diagnostic pair verified; per-product metadata captured; consolidated QA disposition and event interpretation remain open

## Context

The available VALIDATED NISAR GCOV temporal candidate remains held by its provider QA `FAIL`. ECHO already has a bounded OPERA RTC-S1 COG reader and a product-specific masked log-ratio routine. OPERA RTC-S1 is derived from Sentinel-1 and must remain explicitly distinct from NISAR observations.

## Decision

- Add a bounded ASF OPERA RTC-S1 catalog query using the selected WGS84 rectangle and date range. Preserve returned provider features and screen repeated burst, platform, spacing, and product-version identities as metadata candidates only.
- Add a separate pair API that reads the two selected RTC-S1 polarization assets and provider masks for the same bounded AOI, then applies the existing strict grid, acquisition, mask, and pixel-center compatibility checks.
- Preserve per-product QA metadata when available, but do not invent an aggregate `PASS` or `FAIL` disposition. A successful raster calculation is not promoted to a provider-validated or event-level finding.
- Keep NISAR GCOV discovery and QA gates unchanged. OPERA is an alternate NASA-supported validation path, not a substitute or correction for NISAR QA evidence.

## Verification and limits

- Pure catalog tests cover WGS84/date validation, pair grouping, incompatibility separation, candidate-only labels, and result-cap disclosure.
- Pipeline tests check bounded AOI/polarization forwarding and reject duplicate products before raster reads.
- HTTP tests cover the OPERA catalog and pair endpoints, payload validation, and explicit source/QA labeling.
- Earthdata Login authenticated with the configured local netrc; an ASF asset range request returned HTTP 206 after redirects through Cumulus and Earthdata OAuth, with no EULA error.
- A live T024-050660-IW1 Sentinel-1A pair, 2024-05-11 and 2024-06-04, was read from ASF and processed over a 0.01° WGS84 AOI. Both products had identical EPSG:32722 grids and 1,199 common clear pixel centers. The result remains `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`. The HDF5 sidecars provide geometric-accuracy fields, RFI metadata, and processing provenance, but no consolidated QA disposition.
- Earthdata Login authenticated with the configured local netrc. Bounded asset requests for both COGs and HDF5 sidecars returned HTTP 206; full COG, mask, and sidecar reads completed for the pair. The relevant ASF access restriction is no longer blocking these products.
- The previous Firefox interaction verified the map and pair workflow before HDF5 QA details were added. The new inspector summary has not been confirmed against the real record in a populated browser view; see the validation report for this remaining UI verification limit.
- The updated source and measurement record is `data/research/opera-rtc-live-pair-product-qa-2026-11-07.json`; the earlier screenshot predates the HDF5 inspector update.
- The project regression suite passed: 171 tests. Compile checks and `git diff --check` passed.
- The screened NASA OPERA DSWx-HLS optical window is from a different AOI and earlier dates; it is contextual product evidence, not spatially matched corroboration of this pair. This work does not change NISAR discovery, QA requirements, or scientific disposition. OPERA remains a distinct Sentinel-1-derived investigation path, not a substitute for NISAR or independent event validation.
