# OPERA T024 scoped quality review — 2026-11-09

## Result

The retained three-acquisition T024 RTC-S1 series now carries a deterministic, checksum-linked quality review in schema version 2. It separates NASA's published product-validation results, the per-acquisition HDF5 QA metadata, and ECHO's local mask/grid/numerical checks. The series remains `DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES`; the review does not manufacture a provider verdict or resolve the physical cause.

## Per-acquisition evidence

| Acquisition (UTC) | Code-0 clear AOI centers | Invalid AOI centers | RFI metadata | Mitigation | In-band/out-band power ratio |
|---|---:|---:|---|---|---:|
| 2024-05-11 08:49:47 | 1,051 | 148 | Available | `BasedOnNoiseMeas`, time and frequency | 11.76168 |
| 2024-06-04 08:49:46 | 1,043 | 156 | Available | `BasedOnNoiseMeas`, time and frequency | 10.33025 |
| 2025-06-23 08:49:37 | 1,034 | 165 | Available | `BasedOnNoiseMeas`, time and frequency | 11.07321 |

No layover-affected or shadow-affected AOI centers were recorded. The 1,034 centers retained for the series are the intersection of all dates' valid masks and finite positive gamma-zero samples. They cover 1,034 of 1,199 AOI centers. No threshold was applied to the RFI ratios; the metadata do not spatially quantify residual RFI impact in the selected pixels. The geolocation metadata are preserved as reported but are not treated as scene-level certification or proof of temporal co-registration.

JPL reports absolute geolocation, relative geolocation, and terrain-flattening validation-sample requirements and outcomes on its RTC-S1 product page. The review labels this as product validation context and explicitly states that it is not an individual-acquisition or AOI certificate. ASF's mask definitions and per-acquisition mask guidance are linked in the review record and shown in the interface disclosure.

## Interface and record verification

- Firefox headless loaded the T024 case, opened and closed the investigation assessment, then displayed the temporal-series inspector and its **SCOPED QUALITY REVIEW** disclosure.
- The disclosure rendered the JPL validation scope, `NOT PROVIDED` scene-level verdict, `1,034 / 1,199` common support, all three RFI records and mitigations, and links to JPL and ASF primary documentation.
- Screenshot: [`opera-t024-scoped-quality-review-2026-11-09.png`](opera-t024-scoped-quality-review-2026-11-09.png), SHA-256 `b4387d723fe9e8f6c3fac1800a7eb807e7846b178be6809a2be5749c1be2fac0`.
- The new record checksum is `191cac49a1718c3b5c0fd85d2c7ee814c37c484e8ba7462e92aa9cd2c1bae738`; the case manifest and source-linked assessment were updated to this exact hash.
- The retained measurement values and existing assessment relationships did not change. The linked assessment still validates with 11 evidence artifacts; its water explanation remains unresolved and the temporal series remains non-directional evidence.
- `.venv/bin/python -m pytest -q` — **378 passed**.
- Re-running the builder against the retained series reproduces the exact committed series checksum. Series validation reproduces the 1,034-center common support and checks the embedded review against its retained sources.

## Reproduction

```bash
.venv/bin/python tools/research/build_opera_rtc_quality_review.py \
  --series-record data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json \
  --pair-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json \
  --output /tmp/opera-t024-series-quality-review.json
```

This derives the review from the retained source/measurement record and validates it against the linked pair. It does not retrieve new raster data.

## Limits

This is an ECHO-local scoped quality review, not a NASA or ASF QA disposition, independent Cal/Val reproduction, residual-RFI analysis, or scientific finding. It clarifies evidence available for this bounded product comparison; it does not promote the comparison from diagnostic status or alter NISAR QA requirements.
