# VALIDATED GCOV path 4/frame 6 QA screen — 2026-11-13

## Candidate and retrieval scope

This bounded screen evaluated one previously unscreened, full/full metadata
repeat pair from the retained global ASF catalog record
[`validated-gcov-global-time-series-2026-10-09-11-08.json`](../../data/research/validated-gcov-global-time-series-2026-10-09-11-08.json).
The catalog record contains 2,018 scenes and 54 metadata pair candidates. The
selected pair is same-CRID P05036, ascending path 4/frame 6, with a 12-day
interval and matching HH/HV polarization and product configuration:

ASF's [current NISAR availability guide](https://nisar-docs.asf.alaska.edu/availability-overview/)
states that the VALIDATED release began on November 6, 2026 and includes
L-band acquisitions starting October 21, 2026. This provides release context
for the candidate; the exact-product ASF QA results below remain the operative
quality gate.

| Role | Acquisition | Product |
| --- | --- | --- |
| Before | 2026-10-24 11:04:35 UTC | `NISAR_L2_PR_GCOV_034_004_A_006_4005_DHDH_A_20261024T110435_20261024T110509_P05036_N_F_J_001` |
| After | 2026-11-05 11:04:35 UTC | `NISAR_L2_PR_GCOV_035_004_A_006_4005_DHDH_A_20261105T110435_20261105T110510_P05036_N_F_J_001` |

Only each product's canonical 1,441-byte ASF QA summary and product-specific QA
report were retrieved. No HDF5 product metadata, raster arrays, masks, or pixel
measurements were read; no grid-alignment or temporal comparison was performed.

## Provider QA and metadata cross-check

Both exact-product QA summaries have SHA-256
`8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688` and report
`FAIL` for “Passes all `identification` group checks?” The other eight listed
summary checks pass, including file-open, coordinate-grid, calibration, four
decimated-raster validity checks, and QA completion.

The retrieved product reports were parsed with QA software version 17.2.0:

| Product | QA report SHA-256 | Size |
| --- | --- | ---: |
| Before | `ac2f2cfe393ceaf9d85f269f960520a1e6864457e491e9201699a815f70d1a23` | 663,767 bytes |
| After | `32ace7fc0381d873bf2c05f2ac294d7fe2d91663ed6833b29feaabc4bb19c6b3` | 675,957 bytes |

The report metadata contains `instrumentName=LSAR` and
`listOfObservationModes=(NOT SPECIFIED)` for both products. ECHO's pinned
`nisarqa` v17.2.0 cross-check marks these values as source-rule mismatches.
This is a diagnostic cross-check, not ASF per-field attribution: both provider
dispositions remain `FAIL`, and ECHO does not treat the matching rule findings
as permission to ignore the provider gate.

## Disposition

**QA-held; no temporal analysis performed.** This independent path adds two
more exact P05036 product failures to the sampled evidence. It does not prove
that all products in P05036 fail, nor establish the cause of ASF's aggregate
identification result. Any later corrected product or changed QA result must
be retained as a distinct source record and screened anew.

The machine-readable record is
[`validated-gcov-p05036-path4-frame6-qa-2026-11-13.json`](../../data/research/validated-gcov-p05036-path4-frame6-qa-2026-11-13.json)
(SHA-256 `f97f732f383fcd23e7beba880e3eae67d3a24e4492e9cf3501d4d2d9c38cac13`).
Reproduce the bounded screen with:

```bash
.venv/bin/python tools/research/screen_nisar_crid_reprocessing_qa.py \
  --catalog data/research/validated-gcov-global-time-series-2026-10-09-11-08.json \
  --case-id validated-gcov-path4-frame6-2026-11-13 \
  --crid P05036 \
  --scene-id NISAR_L2_PR_GCOV_034_004_A_006_4005_DHDH_A_20261024T110435_20261024T110509_P05036_N_F_J_001 \
  --scene-id NISAR_L2_PR_GCOV_035_004_A_006_4005_DHDH_A_20261105T110435_20261105T110510_P05036_N_F_J_001 \
  --output data/research/validated-gcov-p05036-path4-frame6-qa-2026-11-13.json
```
