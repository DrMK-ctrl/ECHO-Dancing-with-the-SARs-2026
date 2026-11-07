# DSWx-HLS follow-up search near the RTC-S1 acquisitions

## Question

Would a temporally closer NASA optical water-context product make the relationship between the retained OPERA RTC-S1 response and water classifications more testable?

## Catalog search

The screen queried NASA CMR's PO.DAAC `OPERA_L3_DSWX-HLS_V1` collection over the exact RTC-S1 WGS84 AOI `[-51.24, -30.04, -51.23, -30.03]`. Each reference acquisition was searched in a seven-day window on either side, using CMR's `temporal` and `bounding_box` granule search parameters and a 200-result page. The [CMR API documentation](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) defines those searches; a bounding-box match is an intersection and does not establish full AOI pixel coverage.

CMR returned five products near the May 11, 2024 RTC-S1 acquisition and eight near the June 4 acquisition. ECHO selected the nearest granule by absolute acquisition-time offset for each reference:

- May 13 Sentinel-2B DSWx-HLS, `G3006411434-POCLOUD`, at `+2.195181` days from the May 11 SAR acquisition. This is closer than the previously used May 8 product at `−2.804786` days.
- June 2 Sentinel-2B DSWx-HLS, `G3062381976-POCLOUD`, at `−1.804785` days from the June 4 SAR acquisition. This remains closer than the next candidate, June 7 at `+3.195264` days.

The complete candidate metadata, two exact request URLs, hit counts, retrieval timestamp, and raw-response SHA-256 values are retained in [`dswx-hls-followup-screen-2026-11-07.json`](../../data/research/dswx-hls-followup-screen-2026-11-07.json). Recreate the bounded screen with [`screen_dswx_hls_temporal_context.py`](../../tools/research/screen_dswx_hls_temporal_context.py).

## Bounded product review

The selected pair was read with [`evaluate_dswx_hls_aoi.py`](../../tools/research/evaluate_dswx_hls_aoi.py), which checked the asset sizes and CMR MD5 values, retrieved bounded layers, extracted the exact AOI pixel centers, and retained SHA-256 provenance in [`dswx-hls-nearer-rtc-context-2026-11-07.json`](../../data/research/dswx-hls-nearer-rtc-context-2026-11-07.json).

The nearer acquisition did **not** provide usable standard WTR comparison pixels: WTR has zero common-valid AOI centers. WTR-2 has 1,199 common centers and its product-coded water counts change 329→59, but all 329 earlier water-coded cells carry cloud/snow flags in CONF; 2 of 59 later cells carry those flags. The count change therefore does not provide clear optical evidence for the SAR interpretation. WTR-2 is not a second independent water classification, and CONF is a quality/context layer.

This is a quality-limited follow-up, not an additional causal confirmation. The pair reuses the June 2 optical product from the earlier comparison, so the two assessments are not independent corroborations. It does not change the OPERA RTC-S1 diagnostic disposition, clear NISAR QA, establish flood extent, or identify a physical cause.

## Integration

The investigation assessment now links the CMR screen and this bounded optical record as separate evidence artifacts. It records the nearer optical data as `LIMITS_INTERPRETATION` for the water-to-SAR hypothesis and updates that follow-up to `RETRIEVED_QUALITY_LIMITED`. The proposed search for adequately resolved alternative surface-driver evidence remains `NOT_SEARCHED`; the exact RTC-S1 provider QA response remains `PROVIDER_RESPONSE_REQUIRED`.
