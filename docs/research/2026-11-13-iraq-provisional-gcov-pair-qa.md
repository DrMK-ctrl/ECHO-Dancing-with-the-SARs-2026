# Iraq PROVISIONAL GCOV pair: provider QA screen

**Screened:** 2026-11-13 UTC  
**Provider:** Alaska Satellite Facility DAAC (ASF)  
**Collection:** NISAR L2 GCOV PROVISIONAL V1, CRID P05023

## Catalog result

A bounded ASF search covered WGS84 bounds `[43.8, 32.5, 45.0, 33.5]` from
2026-10-01 through 2026-11-12 at `PROVISIONAL` maturity. The retained response
contains 13 product records and six metadata candidate pairs. It is metadata
discovery only; it does not establish provider QA, raster-grid alignment, or
change.

The pair selected for QA screening is the full-coverage, 12-day repeat on
ascending path 13, frame 18:

| Role | Acquisition | Orbit | Product |
| --- | --- | ---: | --- |
| Before | 2026-10-01 02:10:15 UTC | 6167 | `NISAR_L2_PR_GCOV_032_013_A_018_2005_DHDH_M_20261001T021015_20261001T021049_P05023_N_F_J_001` |
| After | 2026-10-13 02:10:15 UTC | 6340 | `NISAR_L2_PR_GCOV_033_013_A_018_2005_DHDH_M_20261013T021015_20261013T021049_P05023_N_F_J_001` |

The products share collection, CRID, path, frame, direction, and HH/HV
polarizations. Their ASF catalog footprints intersect and both report full
frame coverage. These metadata do not prove that the grids align or that a
valid common pixel cohort exists.

## Provider QA

The canonical ASF QA summary for each exact product was retrieved through
ECHO's bounded QA-summary route using local Earthdata authentication. Both
summaries are 1,441 bytes, have SHA-256
`8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`, and
report:

- `FAIL` — “Passes all identification group checks?”
- `PASS` — file open, coordinate-grid metadata, calibration LUT, four
  decimated-raster validity checks, and QA completion.

The identical summary hashes mean these two responses contain identical QA
bytes. ECHO retains the provider's `FAIL`; it does not infer that the other
passing rows clear the failed group. The October product identification
attributes themselves were not read during this screen. Although this result
matches the P05023 failure pattern seen in an earlier pair, the precise
offending metadata values were not re-established for these two products.

## Disposition

**QA-held; no change analysis performed.** No product arrays or backscatter
measurements were read for this pair. ECHO's actual pair-analysis endpoint was
also exercised with these exact catalog records: it returned `QA_HELD`, listed
both roles as held, set `measurement` to `null`, and recorded
`measurement_arrays=NOT_READ` and `change_calculation=NOT_PERFORMED`. The pair
must not support a scientific change conclusion while either provider QA
result is `FAIL`. A new attempt is justified only after an ASF QA summary,
product revision, or processing release changes, or when a distinct
collection/CRID offers a scientifically compatible candidate.

A headless Firefox pass then followed the same flow through the interface:
search the WGS84 area, choose the October 1–13 path 13/frame 18 candidate, and
press **Analyze Pair**. The inspector showed **PAIR HELD AT PROVIDER QA GATE**,
both product QA values as `FAIL`, each source checksum, and stated that no
measurement arrays or comparison result exist. The toast said no measurement
arrays were read, and the map caption said `provider QA held · no comparison
pixels read`. This verifies the visible user path as well as the API disposition;
it does not demonstrate an accepted scientific result.

The machine-readable catalog screen, exact product records, pair metadata, QA
summaries, retrieval timestamps, and artifact checksums are retained in
[`2026-11-13-iraq-provisional-gcov-pair-qa.json`](../../data/research/2026-11-13-iraq-provisional-gcov-pair-qa.json).
Manifest SHA-256: `6a3e2d54c75fef0c843b460b9701caed1203e23b9cf8beecf885b5370ceda76a`.
