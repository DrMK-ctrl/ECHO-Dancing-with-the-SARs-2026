# Candidate case review — Rasuwa, Nepal flood and debris-flow event

**Reviewed:** 2026-11-07
**Status:** Promising research candidate; not selected for scientific analysis.
**Purpose:** Compare a recent NISAR observation pair with independently sourced event evidence while preserving the product QA hold.

## Candidate question

Could a same-configuration NISAR GCOV pair help characterize radar-response changes along the Bhote Koshi/Trishuli corridor after the 26 August 2026 event, and which mapped event and control areas have usable, comparable observations? This is a candidate question only. No NISAR raster values have been read for this case, and no change result or cause has been inferred.

## Event evidence and interpretation limits

- Nepal's Ministry of Home Affairs records a flood on the Bhote Koshi in Rasuwa on 26 August 2026 at 08:40 local time and lists affected districts. [Official notice](https://www.moha.gov.np/en/post/ha-ra-tha-ka-apa-l-11)
- WHO reports the flash floods in the Bhote Koshi and Trishuli corridors. Its early account says a sudden upstream surge and a possible ice-avalanche/temporary-damming mechanism were under assessment; it does not establish a final causal account. [WHO situation page](https://www.who.int/nepal/emergencies/2026-rasuwa-flash-floods)
- Sentinel Asia records the activation requested by Nepal's Department of Hydrology and Meteorology and lists SAR and optical products. Its page describes an EOS-RS Sentinel-1 damage-proxy map observed 28 August, an AIT map combining Sentinel-1 and Sentinel-2, and JAXA ALOS-2 products. These products are relevant context, but any product derived from the same SAR observations is not independent validation of an ECHO result. [Sentinel Asia activation](https://sentinel-asia.org/EO/2026/article20260826NP.html)
- UNOSAT's cumulative extent resource derives from Sentinel-2 imagery acquired 27 August and PlanetScope imagery acquired 26 August. UNOSAT says the analysis is preliminary and not field-validated. Its analysis-extent resource explicitly warns that no mapped extent outside that polygon does not imply no impact. It can define screening strata and identify areas to inspect; it is not ground truth. [Dataset and resource metadata](https://ihp-wins.unesco.org/dataset/nepal-satellite-detected-mudflow-and-rockflow-extent-nepal) · [DOI](https://doi.org/10.63253/1y26ihdq)

The event's physical trigger and the exact boundary between floodwater, mudflow, rockflow, and other surface change remain separate questions. Do not use an observed backscatter difference to resolve causation by itself.

## NISAR catalog candidate

A live ASF metadata query was made on 2026-11-07 around 85.55°E, 28.30°N, for 2026-08-01 through 2026-09-01, selecting PROVISIONAL NISAR GCOV. It returned six product features, including duplicate reprocessing releases.

The pair retained for further evaluation is:

| Role | Acquisition | Scene identifier | Configuration |
|---|---|---|---|
| Before | 2026-08-19 23:39:18 UTC | `NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001` | PROVISIONAL, ascending, path 98/frame 16, HH/HV, 40+5 MHz, CRID P05023 |
| After | 2026-08-31 23:39:18 UTC | `NISAR_L2_PR_GCOV_029_098_A_016_4005_DHDH_A_20260831T233918_20260831T233952_P05023_N_F_J_001` | Same listed configuration; 12 days after the before acquisition and 5 days after the event |

Catalog footprint overlap and matching metadata do not establish pixel-grid co-registration or common valid-pixel coverage. The two acquisitions' observation times are close to one repeat interval, but terrain, hydrology, vegetation moisture, and residual geometric or processing effects still need explicit evaluation. ASF's availability guidance describes PROVISIONAL as calibrated and partially validated with known issues; maturity is not a substitute for inspecting each product's QA evidence. [ASF maturity guidance](https://nisar-docs.asf.alaska.edu/availability-overview/) · [GCOV product guide](https://nisar-docs.asf.alaska.edu/gcov/)

An overlay of the UNOSAT polygon on the two ASF catalog footprints places the entire approximately 37.35 km² polygon inside both metadata footprints. This is a footprint-level geometric check only; it says nothing about valid raster pixels, masks, or usable event/control sample counts.

## QA gate — unresolved

The locally downloaded QA reports and CSV summaries are ignored under `data/products/nepal-2026/qa/` and are not committed. Both summaries report:

- input opens: PASS;
- coordinate-grid metadata: PASS;
- calibration information LUT metadata: PASS, with crosstalk LUT checks skipped;
- decimated backscatter histogram/quality checks for A/B HHHH and HVHV: PASS;
- identification-group checks: FAIL; and
- QA completion without exceptions: PASS.

Both reports show QA software 17.0.0, `instrumentName=LSAR`, and `listOfObservationModes=(NOT SPECIFIED)`. The v17.0.0 validator source expects instrument names `L-SAR` or `S-SAR` and validates the observation-mode value. These two observed metadata discrepancies are sufficient to fail the identification group under that source logic; the summary CSV does not enumerate individual failing checks, so this review does not claim they are the only failures or that the provider has confirmed the cause. [QA v17.0.0 checks](https://github.com/isce-framework/nisarqa/blob/v17.0.0/src/nisarqa/validate/sanity_checks.py)

**Disposition: QA_HOLD.** No scientific comparison should use this pair until the QA failure is reconciled with the product provider and exact validator build. Passing decimated raster checks do not clear the hold.

## Independent extent artifact inspection

The UNOSAT SHP resource was downloaded locally to `data/products/nepal-2026/reference/floodextent_20260826_nepal.zip` for bounded format inspection. The archive is ignored and must not be committed without a confirmed redistribution license. Its SHA-256 is `867b5bebb4881d1b8f88af31df7f784f5db612fa651c911d81d7304bf5be0dda`. GDAL identified one valid MultiPolygon feature in EPSG:32645, with `Shape_Area` about 37.35 km². That geometry is a satellite-derived delineation from the same event period, not independent field validation. UNOSAT's resource description and this file's `Shape_Area` should be reconciled before reporting an area; no ECHO area estimate is made here.

The live catalog snapshot for Nepal is tracked at `data/cases/nepal-2026/catalog.json`. It contains ASF metadata, not pixels. The selected P05023 candidate appears alongside an X05026 reprocessing for each date; the pair must remain pinned to a single processing release.

Machine-readable evidence and source-file hashes for the selected pair and QA artifacts are recorded in [`data/cases/nepal-2026/case-review.json`](../../data/cases/nepal-2026/case-review.json).

## Current decision and next gates

Nepal is a stronger candidate than an event with no timely NISAR before/after coverage because it has a same-configuration PROVISIONAL pair, official event reporting, and a published satellite-derived event extent. It is **not yet selected**: the pair is on QA_HOLD; the reference polygon is preliminary, optical-derived, and not field-validated; and cloud/terrain/seasonal ambiguities require a carefully bounded question and controls.

Next gates:

1. Seek provider reconciliation for both QA identification failures; keep the pair held until then.
2. Confirm licensing and provenance terms for the UNOSAT reference geometry before any tracked copy or redistribution.
3. If QA is cleared, compare product coordinate transforms, cell registration, masks, and shared valid coverage using a small event window and a matched control window; report the access and processing provenance.
4. Define one physical question and conventional baseline before testing competing explanations. Treat the UNOSAT extent as a contextual screening layer, not pixel truth.
5. Revisit the official 2026 challenge statement and judging/submission guidance when the official pages are reachable; the current official challenge-detail URL returned HTTP 502 during this review.

## Competition context checked

The official 2025 awards page defines “Best Use of Science” around valid science/scientific method, “Best Use of Data” around making space data accessible or applying it uniquely, and “Best Use of Technology” around innovative technology use. These are the latest published descriptions located for this review, not confirmed 2026 judging criteria. The official 2025 site reports 10 Global Awards and a multi-stage selection from local judging through global subject-matter-expert review and executive judging. This supports emphasizing a reproducible scientific question, honest evidence, and a clear demonstration, but does not predict a judging outcome. [2025 awards and process](https://www.spaceappschallenge.org/2025/awards/) · [2025 winners](https://www.spaceappschallenge.org/2025/awards/global-winners/)

## Source and artifact record

- ASF query date: 2026-11-07; query point/date/maturity and six features are recorded in the tracked catalog JSON.
- UNOSAT extent archive SHA-256: `867b5bebb4881d1b8f88af31df7f784f5db612fa651c911d81d7304bf5be0dda`.
- NISAR QA reports are local ignored files; no raster values were read for this case.
- This review records research evidence and gates. It does not claim a new SAR detection, causal finding, accuracy score, or validated investigation-engine capability.
