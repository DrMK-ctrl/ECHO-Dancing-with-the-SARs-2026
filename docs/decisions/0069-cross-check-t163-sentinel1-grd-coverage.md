# Decision 0069: Cross-check T163 temporal coverage against Sentinel-1 GRD

**Date:** 2026-11-08  
**Status:** Catalog screen completed; GRD archive adds no independent acquisition dates

## Context

Decision 0068 found only the existing two T163 same-burst observations in the ASF OPERA RTC-S1 catalog for this AOI. A catalog check of the source mission's Sentinel-1 GRD products can determine whether the apparent temporal gap is specific to OPERA processing or reflects the underlying acquisitions. This is a metadata availability check, not a plan to mix GRD and RTC values.

## Result

The ASF Sentinel-1 GRD search for the same AOI and 2014-01-01 through 2026-11-08 returned 486 records over two pages, below the 500-item limit. Only two records match ascending path 163, IW mode, dual VV+VH polarization. Their acquisition windows overlap the two OPERA RTC-S1 observations already used by T163:

- 2024-05-08: GRD `S1A_IW_GRDH_1SDV_20240508T220709_20240508T220734_053785_06893A_877E-GRD_HD` and OPERA RTC-S1 beginning at 22:07:19 UTC.
- 2024-06-01: GRD `S1A_IW_GRDH_1SDV_20240601T220657_20240601T220731_054135_06954B_1893-GRD_HD` and OPERA RTC-S1 beginning at 22:07:19 UTC.

The GRD search therefore does not add temporal observations. Those products represent the same Sentinel-1 acquisitions after a different processing path. Do not count them as independent observations or infer that GRD and RTC measurements are numerically interchangeable.

## Consequences

Close the ASF Sentinel-1 GRD catalog route as a source of additional same-path dates for the current T163 AOI and archive interval. Keep the retained two-date OPERA result diagnostic. Additional SAR chronology requires another scientifically appropriate case or a genuinely different acquisition source; this catalog result alone does not justify raw-GRD retrieval or processing.

## Reproducibility

The full client-returned catalog feature snapshot is retained in [the research record](../../data/research/sentinel1-grd-t163-archive-history-2026-11-08.json), with SHA-256 `ef1de5fd2f8395776247c8981907a777c330262134584e65081fab54fa95aab4`. Query and interpretation limits are documented in the [validation record](../validation/sentinel1-grd-t163-archive-history-2026-11-08.md).
