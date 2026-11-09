# T024 extended HLS L30 candidate screen — 2026-11-09

## Search and selection

The AOI is `[-51.24, -30.04, -51.23, -30.03]`; the linked diagnostic OPERA RTC-S1 acquisitions are 2024-05-11 08:49:47 UTC and 2024-06-04 08:49:46 UTC. NASA CMR was queried for HLS L30 collection `C2021957657-LPCLOUD` in windows ±8 days around those dates. Each response returned HTTP 200 and all reported hits on its first 200-item page.

| Window | CMR hits | Candidates |
|---|---:|---|
| May 3–19 | 1 | `HLS.L30.T22JDM.2024129T131759.v2.0` (May 8) |
| May 27–June 12 | 2 | `HLS.L30.T22JDM.2024153T131804.v2.0` (June 1); `HLS.L30.T22JDM.2024161T131748.v2.0` (June 9) |

The June 1 candidate was the already-screened after-observation, so it was not retrieved again. The June 9 scene was selected as the next distinct acquisition to screen; this was a coverage-search choice, not an expectation of good quality. Exact CMR UMM JSON response bodies, response hashes, result identities, and the retrieval record are retained in [`data/research/hls-l30-vegetation-T024-050661-2026-11-09-jun09.json`](../../data/research/hls-l30-vegetation-T024-050661-2026-11-09-jun09.json) and its linked metadata responses under `data/research/hls-l30-t024-support-screen-2026-11-09/`.

## Measurement and disposition

NASA LP DAAC HLS L30 v2.0 B04, B05, and Fmask were read as bounded COG windows on their native EPSG:32622 grid. The AOI contains 1,152 pixel centers. May 8 has 762 clear-land centers; June 9 has none. Its Fmask value is 194 at all 1,152 centers: cloud bit 1 is set, and aerosol bits 6–7 encode the high aerosol level. Thus common clear-land support is zero (0/1,152); no NDVI difference or SAR association is computed.

The record is a candidate-coverage screen, not a vegetation finding. It cannot support or contradict H4, test vegetation causality, validate the Sentinel-1-derived OPERA pair, or establish an event boundary. H4 remains `UNRESOLVED`; F9 remains `SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE`. The search is limited to the retained ±8-day CMR windows and is not exhaustive.

## Reproduction and verification

Re-run the T024 assessment command in [the preceding HLS sensitivity validation](t024-hls-cutoff-sensitivity-2026-11-09.md), adding:

```bash
  --hls-candidate-screen-record data/research/hls-l30-vegetation-T024-050661-2026-11-09-jun09.json \
  --output data/research/opera-rtc-cross-sensor-investigation-T024-050661-2026-11-09-hls-candidate-screen.json
```

The versioned assessment snapshot is selected by the T024 `investigation.json`; previous snapshots remain retained. Unit tests verify builder linkage, Fmask/assets reproduction, and rejection of tampered counts. The web validator checks the same evidence relationships and prevents directional use of this candidate. A headless Firefox run opened the live T024 assessment, rendered the extended-candidate card and open follow-up, then opened the source inspector and confirmed the CMR response, selected granule, Fmask class counts, and value 194 were present. This verifies the local interface and source navigation, not vegetation causality or SAR validity.

Verification: `.venv/bin/python -m pytest -q` — **390 passed**; `.venv/bin/python -m compileall -q echo tools/research` — passed; `git diff --check` — passed.
