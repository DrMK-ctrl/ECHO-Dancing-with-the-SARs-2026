# Decision 0068: Bound T163 RTC-S1 temporal coverage before extending the SAR series

**Date:** 2026-11-08  
**Status:** Archive-history screen completed; no further same-burst RTC-S1 dates identified for this case

## Context

The T163-349925-IW2 investigation uses a 2024-05-08 / 2024-06-01 Sentinel-1-derived OPERA RTC-S1 pair. The application vision benefits from temporal context, but product pairing across different bursts or orbits cannot be assumed to preserve compatible geometry or spatial support. Repeating short searches around the event would not answer whether the exact burst has other available observations.

## Decision

Screen the full ASF OPERA RTC-S1 catalog interval for the exact T163 AOI and group results by the provider product's repeated-burst identity before attempting to extend its SAR sequence. Treat the result as metadata discovery only. Do not combine neighboring burst IDs or orbits into the T163 temporal series without separately establishing their scientific compatibility.

## Result and consequences

The 2014-01-01 through 2026-11-08 query returned 453 catalog records in two pages, below the 500-item cap. The result contains six repeated-burst series. The exact T163-349925-IW2 series contains two records: 2024-05-08 and 2024-06-01, the already retained pair. This bounds the current ASF RTC-S1 same-burst route for T163; it does not establish global ASF archive completeness, product QA, grid overlap, or absence of observations in other products or providers.

Keep the current two-date RTC-S1 comparison diagnostic. Continue the investigation using already retained independent chronology where suitable, or evaluate a different scientifically appropriate SAR product or case for additional dates. Preserve NISAR as ECHO's primary challenge foundation and label OPERA RTC-S1 as Sentinel-1-derived complementary data.

## Reproducibility

The complete returned feature snapshot is [retained here](../../data/research/opera-rtc-t163-archive-history-2026-11-08.json). Its SHA-256 is `260cc4368e50034be3c91ff1f2f5857124af7082759deb450938bf0c47ee72af`. Query counts, exact burst membership, and limits are in the [validation record](../validation/opera-t163-rtc-s1-archive-history-2026-11-08.md).
