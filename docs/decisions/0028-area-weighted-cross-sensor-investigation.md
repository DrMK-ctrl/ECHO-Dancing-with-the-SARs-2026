# Decision 0028: Add a provenance-linked native-grid spatial association check

**Date:** 2026-11-08
**Status:** Implemented as a diagnostic investigation step for the retained T163 case

## Context

The T163 assessment linked a real Sentinel-1-derived OPERA RTC-S1 backscatter ratio with near-date NASA OPERA DSWx-HLS classifications, but stopped before spatial comparison because the products use different native grids. The case already retained SAR cell corners and measurements plus optical cell polygons and class values. A QA-cleared NISAR pair is still unavailable; this step uses the existing NASA OPERA case without changing the NISAR QA gate.

## Decision

- Transform each retained DSWx-HLS WTR cell footprint into the RTC-S1 projected CRS and intersect the polygons with SAR cells. Use intersection area to calculate each SAR cell's before/after water-class fractions on common valid optical support.
- Do not resample either product. Exclude WTR cells unless both dates have a class in the retained valid set `[0, 1, 2]`; treat codes `[1, 2]` as water, consistent with the source context record.
- Require the SAR common-clear and finite-value masks. Report results across multiple minimum common-valid optical area-coverage thresholds.
- Keep the result diagnostic. The pair has no consolidated provider QA disposition, DSWx-HLS is optical algorithm context rather than SAR validation, and per-cell association is not causation. Do not report inferential statistics because no spatial-dependence-aware evaluation design was established.
- Link the result to the exact SAR and optical source-record checksums. Serve the cell-level record through the interface only when its evidence ID is linked to the case assessment and its hash and identity validate.

## Result on retained T163 records

At a 0.75 common-valid WTR area-coverage threshold, 738 SAR cells were retained. Of these, 710 had at most 0.05 optical water-fraction change; 14 increased and 14 decreased by more than 0.05. Median water-fraction change was zero. The descriptive Pearson correlation between water-fraction change and signed RTC-S1 log-ratio was −0.108. These values do not distinguish the water explanation and do not establish that water did not change; the number of changing cells is limited and the SAR pair remains diagnostic.

The linked assessment keeps the physical-cause disposition unresolved and records this overlay as `DOES_NOT_DISTINGUISH`. It identifies provider-resolved RTC-S1 QA and temporally appropriate observations with more spatially discriminating water changes as useful next evidence.

## Consequences and limits

The investigation workflow now contains an explicit measurement-to-hypothesis spatial check, supports fractional class coverage where grids offset, and exposes its per-cell evidence in the source inspector. The implementation is currently validated on the retained T163 case and controlled geometry fixtures. It is not a generalized cross-sensor science validator, event-boundary detector, or validated flood assessment. DSWx-HLS WTR class `0` is treated as the product's non-water class for this descriptive fraction; the resulting fraction is not subpixel ground truth.

## Reproduction

```bash
.venv/bin/python tools/research/evaluate_rtc_dswx_spatial_support.py
.venv/bin/python tools/research/build_cross_sensor_investigation.py \
  --sar-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical-record data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --catalog-screen-record data/research/dswx-hls-screen-T163-349925-2026-11-07.json \
  --spatial-support-record data/research/opera-rtc-dswx-spatial-support-T163-349925-2026-11-08.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-07.json
```
