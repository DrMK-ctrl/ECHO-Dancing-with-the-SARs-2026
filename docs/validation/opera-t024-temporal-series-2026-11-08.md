# T024 three-date OPERA RTC-S1 series — 2026-11-08

## Result

ECHO retrieved VV, mask, and HDF5 sidecar assets for three ASF OPERA RTC-S1 acquisitions from the exact `T024-050661-IW1` burst, platform S1A, product version 1.0. The primary catalog URL for the 2025 product points to its HDF5 sidecar; its exact GeoTIFF asset URLs are in `additionalUrls`. The reader now resolves only exact ASF host/path product assets listed by the catalog or canonical same-scene siblings, while retaining the catalog byte-size and format checks.

The temporal-series processor verified exact CRS, affine transform, raster window, and selected pixel-center equality. It used a single mask requiring product mask code 0 and finite positive gamma-zero power in all three observations. No reprojection or resampling was performed.

| Acquisition (UTC) | Scene ID | Clear AOI centers |
|---|---|---:|
| 2024-05-11 08:49:47 | `OPERA_L2_RTC-S1_T024-050661-IW1_20240511T084947Z_20240512T065737Z_S1A_30_v1.0` | 1,043 |
| 2024-06-04 08:49:46 | `OPERA_L2_RTC-S1_T024-050661-IW1_20240604T084946Z_20240612T003018Z_S1A_30_v1.0` | 1,043 |
| 2025-06-23 08:49:37 | `OPERA_L2_RTC-S1_T024-050661-IW1_20250623T084937Z_20250702T231945Z_S1A_30_v1.0` | 1,034 |

The strict all-date common support contains 1,034 of 1,199 selected AOI centers. For VV signed gamma-zero log-ratio, the descriptive summaries on that shared support are:

| Comparison | Interval | Median dB | Mean dB | Positive / negative centers |
|---|---:|---:|---:|---:|
| 2024-05-11 → 2024-06-04 | 24.0 days | −1.408 | −2.344 | 270 / 764 |
| 2024-06-04 → 2025-06-23 | 384.0 days | +0.177 | +0.188 | 560 / 474 |
| 2024-05-11 → 2025-06-23 | 408.0 days | −1.252 | −2.156 | 307 / 727 |

The source record includes the per-pixel arrays, masks, exact grid, per-product metadata, input asset hashes, common-support hash, processing versions, and output hashes. The provider QA state remains `PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION`; the series status is `DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES`.

## Scientific limits

The first acquisition is May 11, 2024, so this series has no SAR observation preceding that date. The first observation is a computation reference, not a pre-event baseline. A signed backscatter ratio does not identify water, flood boundaries, or the cause of a response. The all-date mask prevents interval summaries from switching pixel populations, but the provider QA remains unresolved. The three interval summaries share observations and are not independent corroboration. No change category or causal finding is assigned, and this record has not yet been integrated into the case UI.

## Reproduction and verification

- Source catalog snapshot: [`opera-rtc-t163-archive-history-2026-11-08.json`](../../data/research/opera-rtc-t163-archive-history-2026-11-08.json), SHA-256 `260cc4368e50034be3c91ff1f2f5857124af7082759deb450938bf0c47ee72af`.
- Analysis record: [`opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json`](../../data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json), SHA-256 `1024cc94e70c133c49ead3af55d63c8e24470e156898207e9c8fcd1e3290d74b`.
- `.venv/bin/python -m pytest tests/test_opera_rtc.py tests/test_opera_rtc_pipeline.py tests/test_opera_rtc_series_analysis.py -q` — **28 passed**.
- The live builder replay retrieved all three acquisitions through authenticated bounded ASF reads and reproduced the 1,034-center common support and interval summaries above.
- This validates one real series and generic structural gates, not provider QA, causal interpretation, or general support across products.
