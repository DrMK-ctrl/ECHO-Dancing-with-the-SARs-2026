# Decision 0033: Link HLS Landsat vegetation context to the T163 investigation

**Date:** 2026-11-08
**Status:** Implemented for the T163 Rio Grande do Sul diagnostic case

## Decision

Add NASA/USGS Harmonized Landsat and Sentinel-2 L30 Landsat observations as independent optical context for the T163 case. Retain bounded red, near-infrared, and Fmask windows, derive NDVI on common clear non-water land support, and relate the change descriptively to the diagnostic OPERA RTC-S1 response using exact native-grid polygon intersections and area weighting. Do not resample either grid.

This is an evidence test for the investigation workflow, not a causal vegetation test. The Landsat observations are from Landsat 8 and Landsat 9 respectively. HLS processing harmonizes the products, but the platform transition and limited common support remain visible in provenance. At the time, the derived NDVI/SAR association was linked to the compound H3. [Decision 0042](0042-separate-competing-mechanisms.md) supersedes that grouping: the association is now linked to H4 (vegetation-state change) as `DOES_NOT_DISTINGUISH`; H4 remains unresolved and `DESCRIPTIVE_ASSOCIATION_ONLY`.

## Evidence and limits

- Same-AOI HLS L30 acquisitions: `HLS.L30.T22JDM.2024129T131759.v2.0` (Landsat 8 OLI, 2024-05-08 13:17:59.926 UTC) and `HLS.L30.T22JDM.2024153T131804.v2.0` (Landsat 9 OLI, 2024-06-01 13:18:04.978 UTC).
- Landsat precedes the paired Sentinel-1 acquisition by 8.822 hours before and 8.821 hours after. These offsets are retained in the association record and shown on the investigation timeline/card.
- Bounded 32 × 37 source windows retain B04, B05, Fmask, and an AOI-center mask. SHA-256 and byte sizes are recorded; the assessment builder and evidence endpoint verify those assets.
- Common clear-land support is 265 of 1,152 AOI pixel centers (23.0%). Median NDVI change is +0.0746 on this support; the 10th–90th percentile range is −0.0262 to +0.2115.
- On SAR cells with at least 75% common clear-land area, 218 cells remain; median area-weighted NDVI change is +0.0661 and descriptive Pearson r with the VV RTC-S1 log-ratio is −0.290. At 25% and 50% thresholds, respectively, 312 and 265 cells remain, with r = −0.213 and −0.230. No inferential statistics are computed because neighboring cells are spatially dependent and the RTC-S1 pair remains diagnostic.
- This association cannot establish vegetation causality, soil moisture, flood extent, or SAR validity. HLS is optical context and not ground truth. The primary SAR pair still lacks a consolidated provider QA verdict.

## Reproduction

First reproduce the bounded optical screen and spatial association:

```bash
.venv/bin/python tools/research/screen_hls_l30_vegetation.py \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --bbox=-51.24,-30.04,-51.23,-30.03 \
  --before-date 2024-05-08 --after-date 2024-06-01 \
  --before-granule HLS.L30.T22JDM.2024129T131759.v2.0 \
  --after-granule HLS.L30.T22JDM.2024153T131804.v2.0 \
  --output-dir data/research/source-artifacts \
  --output-record data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json

.venv/bin/python tools/research/evaluate_rtc_hls_ndvi_association.py \
  --sar-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --hls-record data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json \
  --output data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json
```

Rebuild the T163 assessment using the retained SAR, DSWx-HLS, spatial-support, polarization, GPM, and SMAP records with `tools/research/build_cross_sensor_investigation.py`; add `--hls-vegetation-record` and `--hls-association-record` for the records above. The builder verifies case/AOI identity, source-record hashes, scene and granule identities, and both bounded pixel-asset hashes. The web API repeats linked-record and pixel-subset integrity checks before exposing source details.

## References

- [NASA/USGS HLS L30 product page](https://lpdaac.usgs.gov/products/hlsl30v020/).
- [HLS v2 User Guide](https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf), including reflectance scaling and Fmask bit definitions.
- Retained source and derived records: `data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json` and `data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json`.
