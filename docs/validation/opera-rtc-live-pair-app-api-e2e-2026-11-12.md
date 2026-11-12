# Live OPERA RTC-S1 pair through ECHO's application API

**Date:** 2026-11-12  
**Result:** The authenticated live pair path returned HTTP 200 and reproduced the retained measurement exactly.  
**Scope:** One T163-349925-IW2 VV pair, 24-day interval, bounded WGS84 AOI.  
**Scientific disposition:** Diagnostic; provider QA has no consolidated PASS/FAIL field in the retrieved sidecars.

## Execution

ECHO was started on loopback only with the T163 case selected. The existing `/api/opera-pair-analysis` endpoint received the two retained ASF catalog records, the retained AOI bounds, and VV polarization. It used the application's Earthdata-authenticated reader to retrieve the two COG measurements, masks, and HDF5 sidecars, then ran the existing grid-compatibility and common-validity analysis.

The two source acquisitions are:

- `OPERA_L2_RTC-S1_T163-349925-IW2_20240508T220719Z_20240509T082403Z_S1A_30_v1.0`
- `OPERA_L2_RTC-S1_T163-349925-IW2_20240601T220719Z_20240602T003623Z_S1A_30_v1.0`

The AOI is `[-51.24, -30.04, -51.23, -30.03]` in WGS84. The returned raster window is 38 × 33 cells; 1,199 centers satisfy the shared AOI selection and common-clear mask.

## Reproduction result

The live API response was compared with the retained pair analysis at [`opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json`](../../data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json):

- all **1,254 of 1,254** `values_db` cells were exactly equal;
- the **valid mask** was exactly equal;
- source scene IDs, AOI bounds, and grid shape matched;
- the live response retained `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON` and `PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION`.

The full live API response and retrieval provenance are retained in [`opera-rtc-live-pair-T163-349925-IW2-2024-11-12-app-e2e.json`](../../data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-12-app-e2e.json). This includes asset checksums and processing metadata; credentials and session tokens are not present.

## Browser walkthrough

Firefox headless opened the T163 case, searched the actual ASF RTC-S1 catalog for the retained AOI and date interval, and returned five catalog items with two repeat-pair candidates. The case's T163 candidate was selected and the live pair endpoint was invoked. The map rendered the descriptive comparison alongside the acquisition details and QA panel.

That walkthrough caught a conflicting map caption: it said provider QA had not been retrieved even though the two HDF5 sidecars had been retrieved and the evidence panel correctly said no consolidated PASS/FAIL verdict exists. The caption now derives its wording from the returned provider-QA status. A follow-up headless Firefox render using the retained authentic pair response confirmed the corrected caption and diagnostic status. The screenshot is [`opera-t163-live-browser-2026-11-12.png`](assets/opera-t163-live-browser-2026-11-12.png).

The ECHO server was bound to `127.0.0.1` and stopped after the check. The WebDriver session was closed. No remote service, visibility, or deployment setting was changed.

## Source-inspector quality review follow-up

A subsequent local Firefox walkthrough opened the assessment's `SAR-RTC-S1-PAIR` source record and confirmed that the inspector now renders its retained scoped quality review in readable form, alongside the raw source JSON and product method scope. It shows `NOT PROVIDED` for provider scene-level verdicts, explains that published product validation is not a per-acquisition certificate, and states that ECHO's bounded grid/mask checks do not override provider QA. The two acquisition disclosures expose their scene identifiers, sidecar dispositions, AOI mask counts, RFI metadata, missing-metadata listing, and sidecar checksums. The pair remains explicitly diagnostic; no QA status or scientific conclusion changed.

This was a UI check against the retained evidence record, not a new data retrieval or independent validation of the measurements. The focused GJS renderer and case-registry tests passed (2 tests). Firefox confirmed both acquisition records, the unresolved provider-QA boundary, the diagnostic disposition, and `provider QA overridden: false`.

A 1440 × 950 Firefox visual pass then checked the inspector's hierarchy and fit. The pair has a human-readable title; the quality summary and diagnostic boundary are visible while the two per-acquisition details remain collapsed; and the modal scrollbar uses the dark interface palette. The captured view is [`opera-rtc-quality-inspector-2026-11-12.png`](assets/opera-rtc-quality-inspector-2026-11-12.png), SHA-256 `594af41f3cb4671c47737ca5b895f185286c1c2a82e56fc759633770b118cf17`.

## Scientific limits

This confirms authenticated retrieval, endpoint integration, and exact numerical reproducibility for the tested pair and AOI. It does not establish an OPERA product-level QA pass, field truth, causal attribution, flood extent, or validity for other pairs. The pair remains diagnostic and unresolved. The independently recomputed Challenge This Finding sensitivity calculations remain descriptive analyses of the same diagnostic evidence.
