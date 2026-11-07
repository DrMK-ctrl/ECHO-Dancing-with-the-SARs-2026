# ECHO strategic direction and research sequence

**Status:** Strategic direction and research backlog. This document records intended outcomes; it does not claim that the proposed methods or capabilities exist or have been validated.

## Identity

> ECHO does not merely search for changes. It investigates what the evidence can justify.

The intended advantage is a transparent scientific investigation process that can extract more defensible knowledge from SAR observations by asking better questions of measurements, metadata, acquisition conditions, temporal patterns, terrain, processing history, and independent context. This is a direction to test, not a claim of novelty or superiority over NASA, ASF, OPERA, or other systems.

## What is established now

- ECHO is a separate, private project grounded in civilian SAR Earth observation and the NASA Space Apps Challenge “Dancing with the SARs.”
- A radar-response difference alone does not establish a physical event or its cause.
- Scientific claims require source provenance, product suitability, documented processing, and validation appropriate to the claim.
- Contradictory evidence, missing coverage, and inconclusive outcomes must remain visible.
- Current software provides ASF catalog discovery across BETA, PROVISIONAL, and VALIDATED GCOV collections, point and map-drawn WGS84 rectangle searches in the local UI, same-orbit-aware metadata pair candidates, a local evidence interface, an allowlisted HDF5 identification-metadata inspector, bounded GCOV array-window reads by pixel indices or WGS84 rectangle, CRS and pixel-center coordinates, and a QA-gated paired-window measurement function with an input/output provenance manifest. An isolated `/api/gunw-catalog` route now provides bounded PROVISIONAL or VALIDATED GUNW metadata discovery for product-path evaluation; the visible interface still uses the GCOV catalog workflow and does not display GUNW pixels. Live browser-to-ASF area search and a reproducible AOI catalog query are validated as metadata discovery only. The timeline lists records returned by the active catalog response and connects them to map footprints and source metadata; users can select among compatible pair candidates returned by the catalog screen. Neither feature implies exhaustive coverage or scientific comparability. Geographic pixel selection has been exercised on one authenticated real product, but provider QA failed for that product. A separate screen retrieved official QA summaries for 13 unique GCOV candidate scenes in the Nepal AOI; all 13 report an identification-group failure. A bounded GUNW screen found provisional products in five queried regions, and all five sampled QA summaries report an identification-group failure. For one Istanbul GUNW item, ECHO retrieved the canonical QA report and selected identification/schema metadata under bounded access; the captured product-specific review is [`istanbul-recent-gunw-pair-qa-review-2026-11-07.json`](../data/research/istanbul-recent-gunw-pair-qa-review-2026-11-07.json). The report is now parsed against the pinned GUNW 1.5.0 product contract; its two reference/secondary observation-mode placeholders match candidate rules in `nisarqa` v17.0.0, and NASA expert guidance on the aggregate failure is recorded separately from the unchanged ASF FAIL. Authenticated bounded GUNW pixel windows have been read for Istanbul and Tehran. Three same-AOI Tehran pair windows cover the same 154 pixel centers and retain provider QA `FAIL` plus the ionosphere-interpolated mask flag; phase summaries were retained separately without phase differencing, correction, displacement conversion, or event interpretation. The real GCOV retrieval-to-map path is now exercised for one QA-held diagnostic window; the GCOV pair-analysis function still has no accepted real-data run, and GUNW analysis is not integrated. Catalog pairing requires distinct known NISAR orbits and nonoverlapping acquisition intervals. The paired function has synthetic unit-test evidence and has not analyzed real NISAR pairs. ECHO has no real-data change finding or investigation engine. The Mozambique, Nepal, and Istanbul GCOV case candidates remain on QA hold. Access probes, QA-summary screens, and fixtures are not scientific change results.
- A fresh global VALIDATED GCOV query for 2026-10-30 through 2026-11-07 returned one P05036 scene acquired on 2026-11-05. Its canonical ASF QA summary reports `FAIL` for the aggregate identification group; its coordinate-grid, calibration, decimated backscatter, and QA-completion checks pass. ECHO completed a bounded authenticated 113 × 98-pixel HHHH window read over a 10,648-center AOI, preserving the QA-held diagnostic disposition and source/array hashes. All selected centers carried `inputDataExceptionMask=768` (`uint16`), which ECHO does not interpret; therefore zero pixels were display-eligible and no raster was shown for this window. The product QA report identifies specification 1.6.0, while the publicly linked GCOV Rev F specification is version 1.5.0 and documents different mask dtype/codes. This mismatch is unresolved; the QA gate and exception exclusions remain closed. The full preview and a compact review record are retained in `data/research/validated-gcov-diagnostic-preview-2026-11-07.json` and `data/research/validated-gcov-diagnostic-window-review-2026-11-07.json`, with the human-readable review in [`2026-11-07-validated-gcov-diagnostic-window.md`](research/2026-11-07-validated-gcov-diagnostic-window.md).

## Strategic ideas to evaluate

These are not implementation commitments:

1. **Investigation beyond detection.** Explore a workflow of observation → detection → competing explanations → evidence testing → revised assessment → next useful observation.
2. **Methods of disciplined reasoning.** Evaluate abductive reasoning, falsification, competing-hypothesis analysis, causal mechanisms, Bayesian methods, and cognitive-bias checks only where they produce testable, inspectable scientific steps. Humanities or literary material may inform product identity, but must not decorate or replace the evidence.
3. **More value from the same data.** Test whether careful use of polarization, geometry, timing, terrain, processing metadata, masks, temporal context, and independent observations can resolve ambiguities without disproportionate computation.
4. **Temporal investigation.** Evaluate observation sequences as incomplete, irregularly spaced records. Keep acquisition time distinct from processing, publication, and retrieval times. Select comparisons by temporal relation to the question and scientific compatibility; examine historical, subsequent, recurring, and seasonal context only where the available observations support it. Distinguish a change that persists or recurs from one that appears in a single comparison.
5. **Robustness and evidence sensitivity.** Test whether findings persist across scientifically defensible comparison dates, baselines, thresholds, and evidence subsets. Report which choices change a result and which do not. Treat robustness as evidence about sensitivity, not as a probability of truth or physical damage.
6. **Purposeful AI.** Consider assistance with hypothesis generation, contradiction and information-gap detection, contextual research, prioritization, and follow-up selection. Keep AI output distinct from deterministic measurements. Measure any claimed benefit against a simpler non-AI baseline; AI must not invent evidence, sources, measurements, or confidence.
7. **Generalizable product support.** Preserve a consistent investigation workflow while allowing product-specific readers, metadata rules, quality checks, and scientific operations. Determine applicability and compatibility from documented product capabilities; do not force incompatible missions or formats through one algorithm to claim broad support. Geographic cases should validate the method, not define location-specific analysis logic.
8. **Map-centered investigation experience.** Explore a flat, interactive geographic workspace connected to observation footprints, an acquisition timeline, supported raster comparisons, findings, and source inspection. Reveal advanced controls as relevant, and show only layers and conclusions supported by the processing state. A global map with on-demand access is a preference to assess, not an approved architecture or a reason to weaken provenance, QA, or resource controls.
9. **A compelling real case.** The user is especially interested in recent, significant events in the Middle East, including Iran and Iraq, while preferring the strongest evidence-supported case anywhere. Geography is not a constraint. In conflict-affected regions, investigate verifiable civilian, environmental, geological, or humanitarian observations only.

## Candidate investigation record

If the research supports an investigation engine, each hypothesis should be inspectable and revisable. A candidate record would connect:

- the observation, source product, acquisition conditions, processing version, and derived measurement;
- the observation's role in the temporal record, the actual acquisition interval, and any known gaps in available coverage;
- evidence that supports, contradicts, or does not distinguish each explanation;
- the physical mechanism and expected observations for each explanation;
- data-quality limits, uncertainty, missing information, and explicit falsification opportunities;
- the reason and provenance for any assessment revision; and
- a useful next observation or analysis, with its expected ability to distinguish explanations and its feasibility.

Use explicit states such as **supported**, **contradicted**, **unresolved**, and **not evaluated** only when their criteria are documented. Do not expose uncalibrated probabilities as confidence.

## Research and implementation gates

1. **Challenge and competition research:** verify the official challenge requirements, current judging criteria, submission expectations, relevant award categories, and prior global winners. Translate findings into project decisions only when supported by current primary sources.
2. **Landscape and gap research:** compare NISAR/ASF products and workflows, NASA OPERA surface-disturbance products, scientific literature, and established geospatial tools. Describe documented strengths and limits; do not invent a gap for competitive positioning.
3. **Case selection:** compare candidate events by authentic and accessible observations, product QA/maturity, temporal and spatial comparability, a specific measurable question, independent reference evidence, and reproducibility. Treat the Middle East interest as a preference, not a geographic restriction.
4. **Scientific baseline:** define one bounded measurement and a suitable conventional detector or workflow before adding an investigation layer. Preserve holdouts and independent reference evidence where available.
5. **Temporal and robustness evaluation:** when adequate observations exist, compare appropriate historical, event-window, and subsequent acquisitions; document gaps and acquisition compatibility. Evaluate sensitivity to defensible dates, baselines, thresholds, and evidence subsets without turning agreement into confidence.
6. **Investigation-method evaluation:** test whether structured alternatives, contradiction checks, or selected AI assistance improve the assessment or next action on the same evidence. Report failure cases and compare complexity and resource cost with the baseline.
7. **Interface integration:** connect geographical discovery, acquisition chronology, supported processing, and evidence inspection as their data contracts become real. Do not display simulated layers or conclusions as measurements.
8. **Architecture decisions:** assess product-specific processing modules, global coverage, and on-demand reads only after the selected case, product access behavior, QA rules, reproducibility needs, and local resource limits are understood.
9. **Demonstration readiness:** present a genuine observation, the initial interpretation, discriminating evidence, any justified revision, and what remains unresolved. Never manufacture an anomaly or a reversal for a memorable presentation.

## Readiness boundary

The current catalog and UI foundation is ready for product-access and case research. A scientific comparison is not ready until a suitable pair passes product and QA review, measurement semantics are verified, grid alignment and common valid coverage are checked, processing is reproducible, and the question has a defensible independent reference or evaluation design. An investigation-engine feature is not ready until those measurement and evidence contracts exist.

## Decision rule

Preserve strategic ideas here until their dependencies are met. Implement a proposed capability only when it addresses a demonstrated need, has an inspectable method and baseline, fits the data and resources, and can be validated without weakening the working scientific foundation.
