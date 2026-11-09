# T163 OPERA RTC-S1 pair quality review

Date: 2026-11-09

Pair: `T163-349925-IW2`, Sentinel-1A, VV, OPERA RTC-S1 v1.0

Disposition: descriptive diagnostic comparison; provider scene QA remains unreported

## Retained observations

| Role | Acquisition start | Scene |
|---|---|---|
| Before | 2024-05-08 22:07:19 UTC | `OPERA_L2_RTC-S1_T163-349925-IW2_20240508T220719Z_20240509T082403Z_S1A_30_v1.0` |
| After | 2024-06-01 22:07:19 UTC | `OPERA_L2_RTC-S1_T163-349925-IW2_20240601T220719Z_20240602T003623Z_S1A_30_v1.0` |

ECHO now attaches a reproducible pair-scoped review to the retained analysis record. It binds both source scene identities, acquisition times, sidecar and raster references/checksums, QA metadata, per-date mask counts, grid-registration metadata, processing description, and hashes of the input and derived arrays. The review is recomputed by the investigation-draft and case-evidence validators; changing its contents without changing the retained inputs is rejected.

JPL's published RTC-S1 accuracy summary describes its validation data, not an individual acquisition or AOI certification. The retrieved sidecars provide no consolidated scene PASS/FAIL verdict. Both record RFI information and `BasedOnNoiseMeas` mitigation in the time/frequency domain; the in-band/out-of-band ratios are 13.3508 and 12.31653. Residual impact within this AOI is not spatially quantified and remains unresolved. Geometric metadata report x/y bias of -0.72/-0.67 m and x/y standard deviation of 0.70/0.62 m for each scene; these are retained metadata, not an independent local accuracy measurement.

Within the 1,199 selected AOI centers, both scene masks mark 1,199 clear centers and zero invalid, shadow-affected, or layover-affected centers. All 1,199 centers are common-clear and finite-positive for the diagnostic log-ratio. Exact grid compatibility and no-resampling conditions are recorded. These checks do not override provider QA, establish independent calibration, or establish an event, boundary, damage, or physical cause. The Sentinel-1-derived result remains distinct from NISAR.

## Reproduction and integrity

From the repository root, rebuild the pair review and refresh any linked content hashes, then validate the retained T163 assessment:

```bash
.venv/bin/python tools/research/build_opera_rtc_pair_quality_review.py \
  --pair-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --output data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --refresh-linked-hashes-under data/research \
  --validate-assessment data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-08.json
```

The linked assessment validates all 23 evidence records. The refresh propagates a changed pair hash through dependent source records and updates the assessment's artifact hashes. Its scientific assessment remains `CAUSAL_INTERPRETATION_UNRESOLVED`.

Pair-record SHA-256: `41e040338b4726766a8e1724e74bac2f211cd71a07190f66711b04a4843603cf`

Review-basis SHA-256: `8f1373a35b1d248560584b8b09663e0f2dd47720cda6e73e317b7debc43adfbd`

## Interface and verification

The retained pair loads through the local case-evidence API and appears in the geographic workspace. Its expandable scoped-quality disclosure presents provider validation scope, mask support, per-scene metadata, source links, residual RFI uncertainty, and the review-basis hash.

Firefox headless rendered the retained T163 map and expanded the disclosure. Checks confirmed the explicit `NOT PROVIDED` provider verdict, human-readable unresolved RFI residual status, 1,199-cell support, and review-basis hash. The [map view](opera-t163-pair-quality-review-2026-11-09.png) and [expanded source inspector](opera-t163-pair-quality-inspector-2026-11-09.png) are retained separately. Their SHA-256 values are `c7141720b8342115520653eff6a9b1850c24b1261925bef991081109eafff1f1` and `f42fe15ff1247fd543dd447412af6d4cd58d363ae99f6ce96935ba71a7e5ed6a` respectively.

Verification: full test suite `385 passed`; Python `compileall` and `git diff --check` passed. A local browser run verified the rendered source disclosure; no provider QA status or physical interpretation was promoted.
