# OPERA RTC-S1 archive-history screen for T163 — 2026-11-08

## Query and result

ECHO queried ASF's OPERA-S1 RTC catalog for the T163 analysis bounds `[-51.24, -30.04, -51.23, -30.03]`, from `2014-01-01` through `2026-11-08`, with a 500-feature limit. The request returned 453 features over two pages and did not reach the cap. The local repeated-burst screen retained 365 features that matched its supported scene-ID and acquisition-time contract, grouped into six burst series, and reported 359 adjacent-date metadata candidates across those series.

Only one series matches the T163 investigation's exact burst ID, `T163-349925-IW2`. It contains exactly these two products:

| Acquisition start (UTC) | Product |
|---|---|
| 2024-05-08 22:07:19 | `OPERA_L2_RTC-S1_T163-349925-IW2_20240508T220719Z_20240509T082403Z_S1A_30_v1.0` |
| 2024-06-01 22:07:19 | `OPERA_L2_RTC-S1_T163-349925-IW2_20240601T220719Z_20240602T003623Z_S1A_30_v1.0` |

The interval is 24 days. These are the already retained T163 pair; the archive-history screen found no further matching same-burst RTC-S1 acquisitions in this query.

## Interpretation boundary

This is a spatial and temporal catalog screen using ASF's `asf-search` client. The retained feature snapshot is the client-returned catalog representation, not a byte-for-byte HTTP response capture. Catalog membership does not establish provider QA, equal raster grids, common valid pixels, measurement suitability, or physical change. The query bounds are the small T163 AOI; this result says nothing about other AOIs or product families. Other burst IDs and orbits are not promoted to T163 time-series observations.

## Reproduction and integrity

- Query implementation: `echo.opera_rtc_catalog.OperaRtcCatalogQuery` and `search_opera_rtc_s1_with_pagination`.
- Result snapshot: [`opera-rtc-t163-archive-history-2026-11-08.json`](../../data/research/opera-rtc-t163-archive-history-2026-11-08.json).
- Snapshot SHA-256: `260cc4368e50034be3c91ff1f2f5857124af7082759deb450938bf0c47ee72af`.
- Retrieval: 453 returned features, 2 pages, result limit 500, `potentially_truncated=false`.
- Software and scientific product QA were not re-run or changed by this metadata-only query.
