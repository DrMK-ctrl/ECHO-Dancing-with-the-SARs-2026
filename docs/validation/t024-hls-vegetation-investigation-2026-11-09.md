# T024 HLS vegetation investigation — 2026-11-09

## Candidate discovery and selection

Case: Rio Grande do Sul T024-050661, AOI `[-51.24, -30.04, -51.23, -30.03]`. The primary observations are OPERA RTC-S1 on 2024-05-11 08:49:47 UTC and 2024-06-04 08:49:46 UTC. Exact-date HLS L30/S30 CMR searches returned no products. The bounded ±3-day windows were 2024-05-08 through 2024-05-14 and 2024-06-01 through 2024-06-07.

| Product | Candidates in before window | Candidates in after window | Deterministic selected pair |
|---|---|---|---|
| HLS L30 v2.0 | `HLS.L30.T22JDM.2024129T131759.v2.0` (May 8) | `HLS.L30.T22JDM.2024153T131804.v2.0` (June 1) | The only pair returned in those date windows |
| HLS S30 v2.0 | `HLS.S30.T22JDM.2024129T132241.v2.0` (May 8); `HLS.S30.T22JDM.2024134T132229.v2.0` (May 13) | `HLS.S30.T22JDM.2024154T132239.v2.0` (June 2); `HLS.S30.T22JDM.2024159T132241.v2.0` (June 7) | May 13 and June 2, nearest by acquisition time to the corresponding SAR dates, selected before pixel inspection |

The candidate window and selection rule are retained here. Product quality and common support were evaluated only after the temporal selection.

## Bounded measurements and results

The L30 screen retained red, narrow-NIR, and Fmask subsets from NASA LP DAAC COGs. Both observations share the exact native grid and AOI-center support. The selected dates were acquired by Landsat 8 (May 8) and Landsat 9 (June 1), respectively 67.53 hours before the corresponding SAR acquisitions.

| L30 result | Value |
|---|---:|
| AOI pixel centers | 1,152 |
| Before-date clear land | 762 |
| After-date clear land | 375 |
| Common clear land | 265 (23.0% of AOI) |
| Common-clear median NDVI change | +0.07461 |
| SAR cells with at least 75% common-clear optical area | 218 |
| Descriptive Pearson r, NDVI change vs. SAR log-ratio | −0.27174 |
| Inferential statistic | Not computed |

This is an area-weighted native-grid overlay without resampling. Neighboring cells are spatially dependent; r is descriptive only. H4 remains `UNRESOLVED`, and the evidence relation is `DOES_NOT_DISTINGUISH`.

The closest S30 pair was also retrieved from the same AOI. Its May 13 observation classified all 1,152 centers as Fmask byte 66; bit 1 (value 2) is the cloud flag, leaving zero paired clear-land centers. The June 2 scene has 997 clear-land centers, but no common clear-land support remains across the pair. ECHO therefore computes neither an NDVI change nor a SAR association for this S30 pair.

The [NASA/USGS HLS User Guide v2.0](https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf) documents the S30/L30 30 m products, Fmask-based QA, and the QA bit definitions. In particular, it identifies bit 1 as cloud and documents aerosol levels in bits 6–7.

## Integration and provenance

The L30 vegetation screen and derived association are linked to the active T024 assessment with checksums and source relationships to the exact SAR pair and optical record. The assessment exposes the source summary through the HLS context card and source inspector. The HLS S30 retrieval remains a separate quality-limited research record because its zero common clear support cannot form a spatial association.

Reproduction from the repository root:

```bash
.venv/bin/python tools/research/screen_hls_l30_vegetation.py \
  --case-id rio-grande-do-sul-cross-sensor-diagnostic-2024 \
  --product L30 --bbox=-51.24,-30.04,-51.23,-30.03 \
  --before-date 2024-05-08 --after-date 2024-06-01 \
  --before-granule HLS.L30.T22JDM.2024129T131759.v2.0 \
  --after-granule HLS.L30.T22JDM.2024153T131804.v2.0 \
  --output-dir data/research/hls-l30-t024-050661 \
  --output-record data/research/hls-l30-vegetation-T024-050661-2026-11-09.json

.venv/bin/python tools/research/evaluate_rtc_hls_ndvi_association.py \
  --sar-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json \
  --hls-record data/research/hls-l30-vegetation-T024-050661-2026-11-09.json \
  --output data/research/hls-l30-ndvi-sar-association-T024-050661-2026-11-09.json

.venv/bin/python tools/research/screen_hls_l30_vegetation.py \
  --case-id rio-grande-do-sul-cross-sensor-diagnostic-2024 \
  --product S30 --bbox=-51.24,-30.04,-51.23,-30.03 \
  --before-date 2024-05-13 --after-date 2024-06-02 \
  --before-granule HLS.S30.T22JDM.2024134T132229.v2.0 \
  --after-granule HLS.S30.T22JDM.2024154T132239.v2.0 \
  --output-dir data/research/hls-s30-t024-050661 \
  --output-record data/research/hls-s30-vegetation-T024-050661-2026-11-09.json
```

The active assessment was rebuilt with the existing T024 source records plus these two HLS records; the case manifest selects the new version and retains the prior assessment. Regression tests verify the source links, common support, association, unresolved H4 state, and rejection of directional promotion.

Verification: `.venv/bin/python -m pytest -q` — **387 passed**; `.venv/bin/python -m compileall -q echo tools/research` and `git diff --check` — passed. A local headless Firefox session opened the T024 case assessment, rendered the Landsat dates, 23.0% common clear-land support, 218 SAR cells, descriptive r, and limitation; clicking the source-inspection action opened the HLS record with both granule IDs. This confirms the current UI integration and source navigation, not the physical vegetation hypothesis or SAR quality.

## Scientific boundary

These optical products provide vegetation spectral context. HLS NDVI is not a direct biomass or soil-moisture measurement; Fmask water classes are not flood ground truth. The L30 association does not establish that vegetation caused the SAR response, does not validate the diagnostic SAR pair, and does not establish a flood extent. OPERA RTC-S1 provider QA still has no consolidated disposition.
