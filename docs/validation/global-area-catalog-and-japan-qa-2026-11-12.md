# Global AOI discovery and NISAR QA gate — 2026-11-12

## Scope

Validated the global map's area-selection and online NISAR GCOV discovery path at Sakurajima, Japan, and Hawaii. This checks live ASF metadata and provider QA, not the scientific validity of a change result.

## Geographic discovery

- In local Firefox, selected a Sakurajima AOI `130.2, 31.2, 131.1, 32.0` (west, south, east, north), ran a VALIDATED GCOV search for 2026-10-24 through 2026-11-05, and opened the 12-day same-path/frame pair candidate in the map investigation workflow.
- In a separate Firefox session, selected the global-view Hawaii rectangle `-158.0806, 16.8784, -154.1286, 20.8304`, searched PROVISIONAL GCOV for 2026-10-01 through 2026-11-11, and received 36 catalog records. Firefox rendered the results in the timeline and map; the selected scene inspector showed its acquisition date, product, orbit, frame, polarization, and source identity. A metadata pair candidate was available. This is a second arbitrary-area browser check, not a validated-change claim.
- Direct ASF catalog screens also returned records in Nepal. Catalog presence and a metadata pair are discovery results only; they do not establish usable pixels or provider QA clearance.

## Inclusive end-date defect

ASF Search receives date-only `end` values as midnight UTC. ECHO's query fields describe the selected end date as inclusive, so `2026-11-05` previously excluded later acquisitions on November 5. The bounded VALIDATED Sakurajima request returned 8 scenes before the fix; widening the search showed November 5 acquisitions. After the fix, the same calendar interval returned 11 scenes, including those acquisitions, and surfaced three metadata-matched 12-day pairs.

The shared formatter now sends the final second of the selected UTC calendar day for NISAR GCOV, GUNW, and OPERA RTC-S1 catalog requests. The same boundary is used by the corresponding research screens. This changes search coverage, not product QA or pair suitability.

## Provider QA and measurement boundary

For the Sakurajima VALIDATED pair, the canonical ASF QA summary for both selected acquisitions returned `FAIL`. The summaries were 1,441 bytes and shared SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`. The browser's pair workflow displayed `PAIR ANALYSIS HELD`, identified the QA failures, and reported that measurement arrays were not read; grid alignment and change calculation were not performed.

A separate bounded single-observation diagnostic read used authentic NISAR GCOV product `NISAR_L2_PR_GCOV_034_003_D_072_4005_DHDH_A_20261024T100217_20261024T100251_P05036_N_F_J_001` and a 0.005° Sakurajima window. The reader retrieved a 56 × 49 HDF5 window (2,744 samples; 2,632 pixel centers in the requested AOI) in EPSG:32652. The provider QA disposition was `FAIL`, and ECHO had zero pixels eligible for display from that window. No measurement layer or change result was produced. This verifies bounded data retrieval only; it is not a visible-measurement success or a QA-cleared analysis.

## Verification

- Local Firefox: Sakurajima pair selection and live provider QA through the UI; Hawaii global-view area selection and catalog search through the UI.
- ASF catalog: Sakurajima inclusive-date query reproduced the newly included end-date acquisitions; Nepal and Hawaii were queried independently.
- `.venv/bin/python -m pytest -q`: **497 passed**.
- `.venv/bin/python -m compileall -q echo tools/research/screen_gunw_qa.py tools/research/screen_gunw_temporal_series.py tools/research/screen_opera_rtc_series.py tools/research/screen_validated_gcov_time_series.py`: passed.
- `git diff --check`: passed.

## Limits

These checks establish that arbitrary WGS84 rectangles can reach the online catalog from two distinct world regions, and that QA holds are preserved in the UI. They do not establish global coverage completeness, suitability for all scene geometries, a QA-cleared NISAR temporal pair, successful display of a valid measurement raster for these AOIs, or a NISAR-derived temporal change assessment. The Hawaii browser query is catalog discovery, while the actual bounded pixel read was performed for Sakurajima and yielded no display-eligible pixels.
