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
- Current software provides ASF catalog discovery, metadata-level pair candidates, a local evidence interface, an allowlisted HDF5 identification-metadata inspector, a reusable bounded GCOV array-window reader with CRS and pixel-center coordinates, and a QA-gated paired-window measurement function with an input/output provenance manifest. The October scene window read verifies authenticated data access only; the paired function has synthetic unit-test evidence and has not analyzed real NISAR pixels. ECHO has no real-data change detector or investigation engine. The Mozambique and Nepal pairs remain on QA hold; access probes and fixture results are not scientific results.

## Strategic ideas to evaluate

These are not implementation commitments:

1. **Investigation beyond detection.** Explore a workflow of observation → detection → competing explanations → evidence testing → revised assessment → next useful observation.
2. **Methods of disciplined reasoning.** Evaluate abductive reasoning, falsification, competing-hypothesis analysis, causal mechanisms, Bayesian methods, and cognitive-bias checks only where they produce testable, inspectable scientific steps. Humanities or literary material may inform product identity, but must not decorate or replace the evidence.
3. **More value from the same data.** Test whether careful use of polarization, geometry, timing, terrain, processing metadata, masks, temporal context, and independent observations can resolve ambiguities without disproportionate computation.
4. **Purposeful AI.** Consider assistance with hypothesis generation, contradiction and information-gap detection, contextual research, prioritization, and follow-up selection. Keep AI output distinct from deterministic measurements. Measure any claimed benefit against a simpler non-AI baseline; AI must not invent evidence, sources, or confidence.
5. **Selective, on-demand data access.** Favor bounded, reproducible reads where product formats permit them. A global interactive map with on-demand SAR access is a user preference to assess later, not an approved architecture or a reason to weaken provenance, QA, or resource controls.
6. **A compelling real case.** The user is especially interested in recent, significant events in the Middle East, including Iran and Iraq, while preferring the strongest evidence-supported case anywhere. Geography is not a constraint. In conflict-affected regions, investigate verifiable civilian, environmental, geological, or humanitarian observations only.

## Candidate investigation record

If the research supports an investigation engine, each hypothesis should be inspectable and revisable. A candidate record would connect:

- the observation, source product, acquisition conditions, processing version, and derived measurement;
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
5. **Investigation-method evaluation:** test whether structured alternatives, contradiction checks, or selected AI assistance improve the assessment or next action on the same evidence. Report failure cases and compare complexity and resource cost with the baseline.
6. **Architecture decisions:** assess global coverage and on-demand reads only after the selected case, product access behavior, QA rules, reproducibility needs, and local resource limits are understood.
7. **Demonstration readiness:** present a genuine observation, the initial interpretation, discriminating evidence, any justified revision, and what remains unresolved. Never manufacture an anomaly or a reversal for a memorable presentation.

## Readiness boundary

The current catalog and UI foundation is ready for product-access and case research. A scientific comparison is not ready until a suitable pair passes product and QA review, measurement semantics are verified, grid alignment and common valid coverage are checked, processing is reproducible, and the question has a defensible independent reference or evaluation design. An investigation-engine feature is not ready until those measurement and evidence contracts exist.

## Decision rule

Preserve strategic ideas here until their dependencies are met. Implement a proposed capability only when it addresses a demonstrated need, has an inspectable method and baseline, fits the data and resources, and can be validated without weakening the working scientific foundation.
