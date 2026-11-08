# Decision 0070: Measure RTC-S1 temporal series on common support

**Date:** 2026-11-08  
**Status:** Reusable processor implemented and exercised on three real diagnostic acquisitions

## Context

The two-date T024 RTC-S1 analysis could not show whether its spatial response varied at a later acquisition. The ASF exact-burst catalog includes a 2025 S1A scene for the same T024-050661-IW1 burst. A temporal comparison is only meaningful if the observations share product identity, viewing geometry, pixel grid, and the same valid centers. Pairwise masks can otherwise produce different spatial populations from one interval to the next.

## Decision

Add a deterministic RTC-S1 time-series processor that:

- accepts at least three chronologically ordered observations from one exact burst, platform, spacing, product version, and polarization;
- requires exact CRS, affine transform, AOI window, and pixel-center selection equality, with no resampling;
- forms one common support clear, finite, and positive in every observation;
- reports adjacent-interval and first-observation dB comparisons on that shared support;
- retains each source product, mask, QA metadata, processing versions, and input/output checksums; and
- keeps the result diagnostic when ASF provides no consolidated provider QA verdict.

Intervals share observations and are not independent corroboration. The first observation is a computational reference only; it must not be described as a pre-event baseline unless the acquisition date supports that description.

## Real-data exercise

The first series uses three same-burst, same-platform S1A VV observations over the T024 AOI:

1. 2024-05-11 08:49:47 UTC
2. 2024-06-04 08:49:46 UTC
3. 2025-06-23 08:49:37 UTC

The reader established exact grid and AOI-center equality. The common strict mask retains 1,034 of 1,199 AOI centers across all three dates. Median signed gamma-zero changes on this support are −1.41 dB for the 24-day interval, +0.18 dB for the 384-day interval, and −1.25 dB from the first to third acquisition over 408 days. The first observation is May 11, 2024; this series contains no earlier SAR baseline. The values describe radar response only and do not establish that a flood, a cause, or a physical surface change produced them.

Each product's sidecar metadata has no consolidated QA PASS/FAIL field. The result remains `DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES`; no provider QA gate is cleared. The series currently exists as a reproducible analysis record and is not yet connected to the investigation interface.

## Reproduction and limits

The provider catalog result is retained in [`opera-rtc-t163-archive-history-2026-11-08.json`](../../data/research/opera-rtc-t163-archive-history-2026-11-08.json), SHA-256 `260cc4368e50034be3c91ff1f2f5857124af7082759deb450938bf0c47ee72af`. The analysis record and detailed verification are in the [validation report](../validation/opera-t024-temporal-series-2026-11-08.md).

This exercise validates bounded retrieval and deterministic multi-date measurement on one retained AOI. It does not validate the processor for other missions, products, geographies, or independent ground truth. The assessment remains unresolved until the source QA and relevant independent context are sufficient for the stated question.
