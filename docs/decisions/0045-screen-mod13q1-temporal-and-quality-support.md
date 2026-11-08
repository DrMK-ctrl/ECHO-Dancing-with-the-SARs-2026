# Decision 0045: Screen MODIS MOD13Q1 before treating it as vegetation evidence

Date: 2026-11-08

## Context

The T163 HLS Landsat and Sentinel-2 screens retained limited common clear-land support. A NASA MODIS/Terra MOD13Q1 Version 6.1 candidate offers a finer 250 m native grid over the roughly 1 km AOI. MOD13Q1 is a 16-day composite: its per-pixel selected observation day can differ across the composite window and from the nominal period dates.

## Decision

Screen the exact two SAR-date composite periods on the MODIS native grid. Retain the NASA per-pixel vegetation QA, pixel-reliability rank, land/water class, and selected composite day. Do not calculate NDVI change or NDVI/SAR association unless paired pixels pass the declared quality, land-support, timing, and common-support requirements.

Use a strict suitability mask: valid NDVI; MODLAND DetailedQA class 0; SummaryQA reliability rank 0 (`Good Data / Use with confidence`); land/water class 1; and no adjacent-cloud, mixed-cloud, snow/ice, or shadow flags. This is a conservative screen and does not imply that other MOD13Q1 classes are universally unusable.

## Result

The AOI contains 21 MODIS pixel centers. None is marked as land by the MOD13Q1 land/water QA class. The earlier composite has five SummaryQA rank-0 pixels and 13 marginal pixels; the later composite has zero rank-0 pixels and 20 marginal pixels. No cells pass the paired strict screen. The selected earlier-period pixel dates are 14, 15, and 22 May, 6–14 days after the 8 May SAR acquisition; later selected dates are 1 and 7 June. The pair therefore fails both land-support and strict paired-QA gates, and its per-pixel temporal support is not uniformly aligned to the SAR acquisitions.

Classify this candidate as `QUALITY_AND_TEMPORAL_SUPPORT_LIMITED_NOT_A_VEGETATION_TEST`, link it to H4 as `LIMITS_INTERPRETATION`, and mark follow-up F9 `RETRIEVED_QUALITY_LIMITED`. H4 remains unresolved. No NDVI difference, spatial association, causal inference, or SAR QA change is made.

## Consequences

ECHO now records a NASA candidate through discovery, bounded retrieval, product-specific QA/date screening, evidence linkage, and an explicit inconclusive outcome. The candidate closes this particular MOD13Q1 route; it does not justify repeatedly searching the same composite periods. A materially better-supported independent vegetation observation would need its own scoped test.

The four original HDF granules are not committed because they total about 620 MB. Their CMR identifiers, NASA source links, byte sizes, SHA-256 checksums, and 21 bounded pixel records are retained in the linked screen record. The screen can be regenerated using [`screen_mod13q1_vegetation.py`](../../tools/research/screen_mod13q1_vegetation.py) after downloading those exact granules.

References: [NASA LP DAAC MOD13Q1 Version 6.1](https://doi.org/10.5067/MODIS/MOD13Q1.061) and the [MOD13 Version 6.1 User Guide](https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf), especially the MOD13Q1 QA and pixel-reliability tables.

See the [validation record](../validation/mod13q1-vegetation-screen-T163-2026-11-08.md).
