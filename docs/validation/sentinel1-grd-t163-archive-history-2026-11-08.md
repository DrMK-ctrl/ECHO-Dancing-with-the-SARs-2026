# Sentinel-1 GRD archive-history screen for T163 — 2026-11-08

## Query

ASF's Sentinel-1 catalog was queried for the exact T163 analysis bounds `[-51.24, -30.04, -51.23, -30.03]`, from `2014-01-01` through `2026-11-08`. The requested products were `GRD_HD`, `GRD_MD`, `GRD_HS`, and `GRD_MS`, with a maximum of 500 results. The search returned 486 features in two pages and did not reach the result cap.

The returned path-163 features are:

| Start (UTC) | Stop (UTC) | Platform/orbit | Mode/polarization | Product |
|---|---|---|---|---|
| 2024-05-08 22:07:09 | 22:07:34 | S1A / 53785 | IW / VV+VH | `S1A_IW_GRDH_1SDV_20240508T220709_20240508T220734_053785_06893A_877E-GRD_HD` |
| 2024-06-01 22:06:57 | 22:07:31 | S1A / 54135 | IW / VV+VH | `S1A_IW_GRDH_1SDV_20240601T220657_20240601T220731_054135_06954B_1893-GRD_HD` |

Both acquisition windows overlap the corresponding T163 OPERA RTC-S1 acquisitions. The GRD catalog records therefore describe the same two acquisitions through a different processing product, rather than additional dates in the SAR time series.

## Interpretation boundary

This is ASF catalog metadata returned by `asf-search` 14.1.0. The retained snapshot is the client-returned GeoJSON representation, not a byte-for-byte HTTP response capture. Catalog results do not establish provider QA, pixel support, measurement validity, cross-product numerical compatibility, or physical change. No GRD files were downloaded or processed. The result is limited to the queried AOI, date interval, platform, and product levels.

## Integrity and reproduction

- Snapshot: [`sentinel1-grd-t163-archive-history-2026-11-08.json`](../../data/research/sentinel1-grd-t163-archive-history-2026-11-08.json).
- Snapshot SHA-256: `ef1de5fd2f8395776247c8981907a777c330262134584e65081fab54fa95aab4`.
- Retrieval: 486 results, 2 pages, maximum 500, `potentially_truncated=false`.
- ASF's [official search manual](https://docs.asf.alaska.edu/asf_search/BestPractices/) documents Sentinel-1 catalog queries and paginated `search_generator()` use. ASF describes GRD as amplitude data suited to applications such as RTC generation in its [dataset guide](https://docs.asf.alaska.edu/datasets/using_ASF_data/).
