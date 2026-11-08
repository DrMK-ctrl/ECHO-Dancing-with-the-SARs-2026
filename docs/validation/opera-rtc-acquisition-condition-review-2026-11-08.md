# OPERA RTC-S1 acquisition-condition review

Date: 2026-11-08

## Scope

Compared retained ASF/OPERA metadata for the exact T024 and T163 Sentinel-1-derived RTC-S1 pairs. The review consumes each pair record and its checksum-linked product sidecar metadata. It does not retrieve new satellite products or read raster pixels.

## Results

- T163: documented platform, product configuration, processing, DEM, and reported geometric-accuracy fields match. The per-burst RFI ratio is 13.3508 before and 12.31653 after. No incidence-angle field or spatially matched RFI evidence is retained.
- T024: the same documented configuration groups and geometric-accuracy metadata match. The per-burst RFI ratio is 11.76168 before and 10.33025 after. No incidence-angle field or spatially matched RFI evidence is retained.
- Both derived reviews identify the source pair checksum and each sidecar checksum. Their source links are re-derived and verified by the assessment builder and web validator.
- Both investigation assessments link the review to H5 as `DOES_NOT_DISTINGUISH`, `UNRESOLVED`, and `NOT_TESTABLE_WITH_RETAINED_EVIDENCE`. Follow-up F10 is `RETRIEVED_QUALITY_LIMITED`.

## Verification

- Synthetic contract tests check matching/differing fields, required-field failure, wrong-source rejection, assessment integration, lineage, and record validation.
- Focused suite: `.venv/bin/python -m pytest -q tests/test_opera_rtc_conditions.py tests/test_cross_sensor_investigation.py tests/test_case_records.py tests/test_web.py` — 53 passed.
- Full suite: `.venv/bin/python -m pytest -q` — 284 passed; compilation and `git diff --check` passed.
- Both regenerated assessments pass `echo.web._validate_assessment_record`.
- Headless Firefox opened the T163 assessment, displayed both burst values and the metadata limits, then opened the linked acquisition-condition source record through the inspection button.

## Interpretation boundary

The differing RFI values are single-burst metadata, not a spatially resolved AOI measurement. Their numerical difference is not interpreted as a causal signal or scene-level clearance. The matching geometric-accuracy metadata do not establish registration. Both SAR comparisons remain diagnostic because the provider sidecars have no consolidated QA verdict.
