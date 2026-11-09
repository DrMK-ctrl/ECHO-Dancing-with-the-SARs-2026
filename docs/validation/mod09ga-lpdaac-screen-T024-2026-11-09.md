# T024 Terra MODIS MOD09GA screen through LP DAAC — 2026-11-09

## Result

The T024 SAR interval's two exact-date Terra/MODIS MOD09GA products were retrieved from NASA LP DAAC and screened over the T024 AOI at their native grids. Six common 500 m centers were present. All six passed the product's red/NIR band-quality fields, but none passed the paired vegetation gate because the associated 1 km state QA reports cloud-state code `1` and land/water class `2` or `3`. The before and after dates each had five class-2 centers and one class-3 center. No paired NDVI difference or SAR association was calculated.

The candidate is `RETRIEVED_QUALITY_LIMITED`. The T024 assessment links it to H4 and the open vegetation follow-up, while retaining `H4_VEGETATION_STATE_CHANGE = UNRESOLVED` and overall `CAUSAL_INTERPRETATION_UNRESOLVED`. This optical context does not clear the diagnostic Sentinel-1-derived OPERA pair's provider-QA status and does not establish a vegetation or flood cause.

## Access and processing

Earthdata Login using the local netrc configuration succeeded. The May 11 granule's LAADS OPeNDAP route returned HTTP 404; the June 4 granule was served successfully by LAADS in ten bounded requests (138,965 response bytes). For the unavailable May 11 file, the screener used its exact CMR-linked LP DAAC protected link. A one-byte LP DAAC range check returned HTTP 206 and the full fallback download returned HTTP 200. The screener validates the LP DAAC host and product path, limits each fallback download to 256 MiB, records a full-file SHA-256, and reads `sur_refl_b01_1`, `sur_refl_b02_1`, `QC_500m_1`, and `state_1km_1` through GDAL HDF4 subdatasets. It crops native windows with `gdal_translate -srcwin`; it does not reproject or resample. The temporary fallback granule and GeoTIFF windows are removed after processing.

The live CMR JSON feed omits a `hits` field; the screener reads the result total from the `CMR-Hits` response header. It requests pages until all reported entries are accounted for, records each page URL, byte count, and SHA-256, and fails closed if the total changes or pages are incomplete. Both exact-date queries returned two entries on page 1, including the neighboring MODIS tile; ECHO independently selected the AOI tile `h13v12`.

| Role | MOD09GA granule | HTTP | Bytes | SHA-256 |
|---|---|---:|---:|---|
| Before (LP DAAC fallback) | `MOD09GA.A2024132.h13v12.061.2024134233435` | 200 | 79,352,014 | `c9e39ae824ed70c245df2bb19fc23142846078a7c9277fc09e78f5230588fdc8` |
| After (LAADS OPeNDAP subsets) | `MOD09GA.A2024156.h13v12.061.2024158064357` | 10 × 200 | 138,965 response bytes | Per-response SHA-256 values in the structured record |

The full structured record is [`mod09ga-vegetation-candidate-T024-050661-2026-11-09.json`](../../data/research/mod09ga-vegetation-candidate-T024-050661-2026-11-09.json). It retains the exact CMR granule IDs and response checksums, each route's disposition, the fallback download hash, acquisition window, AOI bounds, raw pixel values, decoded QA fields, and derived acceptance state. The full source products are not retained in the repository.

## Reproduction

From the repository root:

```bash
.venv/bin/python tools/research/screen_mod09ga_vegetation.py \
  --pair-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json \
  --case-id rio-grande-do-sul-cross-sensor-diagnostic-2024 \
  --output /tmp/mod09ga-vegetation-candidate-T024.json
```

Rebuild the active case assessment with the inputs listed in [the T024 HLS sensitivity validation](t024-hls-cutoff-sensitivity-2026-11-09.md) and the soil-moisture and HLS candidate arguments listed in [the T024 availability validation](t024-independent-soil-moisture-availability-2026-11-09.md). Add:

```bash
  --mod09ga-screen-record data/research/mod09ga-vegetation-candidate-T024-050661-2026-11-09.json \
  --output data/research/opera-rtc-cross-sensor-investigation-T024-050661-2026-11-09-soil-moisture-mod09ga-screen.json
```

The case manifest selects the resulting assessment. The MOD09GA card reports the common and accepted sample counts and exact state-QA code sets, and opens the checksummed source record.

## Verification

- The two protected full-granule reads completed with HTTP 200; their byte counts and SHA-256 values are above and in the structured record.
- The native-grid screen returned 6 common centers, 0 strict paired land centers, and an empty paired-NDVI list.
- The assessment builder retained the MOD09GA screen as a NASA optical, quality-limited evidence artifact. H4 and the causal assessment remained unresolved.
- Local `/api/cross-sensor-assessment` and `/api/investigation-evidence` requests returned HTTP 200 for the active case and linked MOD09GA record.
- Headless Firefox opened the T024 investigation, showed six common centers, zero QA-eligible samples, land/water codes `2, 3`, cloud-state code `1`, and the unresolved causal disposition. The source inspector displayed both exact granule identities and the recorded source checksum.
- `.venv/bin/python -m pytest -q` — **397 passed**; `compileall` and `git diff --check` passed.
- Regression coverage includes the two T024 source-link/QA tests in `tests/test_cross_sensor_investigation.py` and the multi-page CMR completeness case in `tests/test_mod09ga_cmr_pagination.py`.
