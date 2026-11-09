# Decision 0096: Bound the flood investigation to independent evidence

**Date:** 2026-11-09
**Status:** Baseline selected; real-case validation gates remain unmet

## Context

The project charter leaves its bounded scientific objective and evaluation method open. ECHO already computes a descriptive signed gamma-zero log ratio on compatible, common-valid OPERA RTC-S1 grids, and its investigation workflow links that measurement to competing explanations. The current T024 and T163 pairs are diagnostic: neither has a consolidated provider QA verdict. Their retained measurements cannot support a validated flood-change claim.

The optical water context is useful but limited. NASA/JPL describes DSWx-HLS as driven by Harmonized Landsat and Sentinel-2 optical observations, while DSWx-S1 is driven by Sentinel-1; DSWx-NI is listed as under development. DSWx-S1 therefore cannot serve as independent corroboration of a Sentinel-1-derived RTC-S1 result. DSWx-HLS can provide cross-sensor context when its acquisition timing and cloud/quality masks support the question, but a classified product is not ground truth. NASA's Rio Grande do Sul flood-depth example itself combines DSWx-HLS extent with SRTM terrain, and CEMADEN's regional inundation map is model-derived using gauge levels, HEC-RAS/HAND, terrain, GloFAS, and Planet imagery. These products have distinct roles and limitations.

## Decision

Use the already implemented native-grid signed gamma-zero log ratio, `10 * log10(after / before)`, as ECHO's simple descriptive SAR response baseline for a candidate flood investigation. Do not add a flood segmentation threshold or claim an extent product from this measurement alone.

The bounded investigative question is:

> Within the exact shared valid support of a compatible SAR pair, does a quality-screened, temporally suitable observation of surface-water state explain the location and direction of the measured SAR response better than the competing explanations and known acquisition/product limitations?

Treat the evidence in separate roles:

- SAR backscatter and the log-ratio are the primary measurements of radar response.
- DSWx-HLS or another independently sourced optical water observation may provide cross-sensor evidence only on its own valid, cloud-screened, temporally compatible support.
- DSWx-S1 is a related Sentinel-1-derived product and is not independent confirmation of RTC-S1.
- Gauge records, official event timelines, and model-derived inundation products provide hydrologic or event context. They do not independently validate a pixel-scale SAR boundary unless their measurement and spatial support justify that specific comparison.
- A missing, cloudy, mistimed, or scale-incompatible reference remains a coverage limitation; it is not a negative observation.

Before calling a real result validated, require product-specific QA and suitability review, exact source and processing provenance, verified compatible acquisition geometry and grids, explicit common-valid coverage, and an independent reference suitable for the stated claim. If an extent classifier is later justified, select and tune it on development data and evaluate it against separate, temporally aligned reference data; report coverage and error measures on that reference and account for spatial dependence. Do not describe cross-sensor association as causation or as independent validation when observations or algorithms share source data.

## Current case fit

The retained T024 OPERA pair spans May 11 to June 4, 2024 and contains 1,043 measured pixels on a 1,199-pixel AOI grid. The T163 pair spans May 8 to June 1 and contains 1,199 measured pixels on its 1,199-pixel grid. Both are diagnostic Sentinel-1-derived OPERA observations with no consolidated provider QA disposition. Neither is eligible for a validated SAR flood result.

The retained shared DSWx-HLS context has acquisitions on May 8 and June 2. Its WTR-2 comparison contains 1,199 common valid centers, with water-class counts of 135 before and 59 after; 99 of the 135 before-date water-class centers overlap the recorded cloud/snow confidence flags, compared with 2 after-date centers. These counts make this a quality-limited comparison, not an independent flood-boundary truth set. The discrepancy is a useful investigation constraint: the present evidence does not establish that surface-water change explains the SAR response.

T163 is the more complete retained workflow-development case because its SAR pair covers the full retained AOI grid and its current case record includes linked optical, precipitation, temporal-series, acquisition-condition, and source-availability evidence. This is a choice for exercising ECHO's investigation workflow only. It is not a scientific case selection, QA clearance, or claim that T163 explains the event. T024 remains linked to its own distinct pair and MODIS/HLS evidence.

## Research basis

- Li et al. (2018), [An automatic change detection approach for rapid flood mapping in Sentinel-1 SAR data](https://doi.org/10.1016/j.jag.2018.05.023), uses log-ratio data within a multi-stage change-detection method and evaluates reference-image selection; it does not justify interpreting a raw ratio as a flood map.
- Felix et al. (2025), [Optimizing change detection methods for flood mapping using polarimetric SAR](https://doi.org/10.1109/jstars.2025.3628450), reports that the preferred reference acquisition and detector can vary by event and study area. This supports sensitivity analysis before adopting a fixed event baseline; its Sentinel-1 polarimetric results are not automatically transferable to NISAR GCOV.
- NASA/JPL, [OPERA DSWx product suite](https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite/), describes the distinct HLS optical and Sentinel-1 DSWx inputs and lists DSWx-NI as under development.
- NASA Earth Observatory, [Southern Brazil Submerged](https://science.nasa.gov/earth/earth-observatory/southern-brazil-submerged-152880/), identifies DSWx-HLS and SRTM as inputs to its flood-depth estimate; the estimate is contextual model output, not independent per-pixel flood truth.
- CEMADEN, [Rio Grande do Sul inundation technical note 469/2024](https://www.gov.br/cemaden/pt-br/assuntos/monitoramento/notas-tecnicas/nota-tecnica-no-469-2024-sei-cemaden-mapeamento-das-manchas-de-inundacoes-e-enxurradas-do-desastre-ocorrido-no-rio-grande-do-sul-em-abril-maio-2024/), describes a regional inundation mapping workflow using gauge levels, HEC-RAS 2D, HAND, terrain, GloFAS, and Planet imagery. Its output must retain this modeled/mixed-source role.

## Consequences and limits

- The existing log-ratio implementation remains the simple measurement baseline; this decision does not add a detector, threshold, or result.
- T024 and T163 can exercise evidence linkage and uncertainty handling but cannot validate flood extent or establish the event's cause.
- A future case must pass the reference, QA, temporal-alignment, and support gates above before ECHO reports classifier performance or a validated physical finding.
- This establishes a measurable direction for the research backlog, not a claim that ECHO's investigative method is scientifically superior to established tools.
