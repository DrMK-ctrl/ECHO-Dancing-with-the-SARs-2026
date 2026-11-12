# Investigation method foundations — 2026-11-12

## Purpose

This note translates the project lead's research framing into engineering principles for ECHO. Chamberlin's multiple-working-hypotheses method and Platt's strong-inference essay are methodological inspiration; neither is a SAR measurement method, a validation dataset, or evidence for a physical explanation in a case.

## Source review

- T. C. Chamberlin, “The Method of Multiple Working Hypotheses,” *Science* 15(366), 92–96 (1890), DOI [10.1126/science.ns-15.366.92](https://doi.org/10.1126/science.ns-15.366.92); bibliographic record: [PubMed PMID 17782687](https://pubmed.ncbi.nlm.nih.gov/17782687/).
- J. R. Platt, “Strong Inference: Certain systematic methods of scientific thinking may produce much more rapid progress than others,” *Science* 146(3642), 347–353 (1964), DOI [10.1126/science.146.3642.347](https://doi.org/10.1126/science.146.3642.347); [PubMed PMID 17739513](https://pubmed.ncbi.nlm.nih.gov/17739513/).
- NASA, [Get to Know SAR — Overview](https://science.nasa.gov/mission/nisar/get-to-know-sar/), updated 2026-06-02. NASA describes the return as dependent on surface roughness and electrical properties, and explains side-looking geometry, polarization, wavelength, and cases where wind-roughened water can return brightly.
- NASA, [NISAR Polarimetry](https://science.nasa.gov/mission/nisar/polarimetry/), updated 2026-06-02. The page relates polarimetric returns to surface electrical and geometric properties and notes that roughness and soil moisture both affect the return.
- Alaska Satellite Facility, [Introduction to SAR](https://hyp3-docs.asf.alaska.edu/guides/introduction_to_sar/). ASF describes amplitude as a return-strength measurement affected by roughness, geometry, wetness, dielectric properties, wavelength, and scattering mechanisms; it distinguishes amplitude from phase-based interferometry.

## Consequences for ECHO

1. Keep multiple plausible mechanisms visible while evidence is incomplete. Do not make the first plausible explanation the default conclusion.
2. State what each hypothesis predicts, what observation could weaken it, what evidence is required, and which conditions would leave the test inconclusive. ECHO's existing hypothesis and follow-up contracts already encode these fields.
3. Treat evidence relationships as scoped claims. `SUPPORTS`, `CONTRADICTS`, `DOES_NOT_DISTINGUISH`, and `LIMITS_INTERPRETATION` must remain tied to a specific hypothesis, source, test, and review basis. A missing relationship is unassessed, not negative evidence.
4. Test analytical sensitivity only across declared, scientifically comparable variants. Record changes in dates, polarization, mask, threshold, and common spatial support. When the support changes, show the cohort difference; do not describe it as a like-for-like comparison. Stability across tested settings is a limited robustness observation, not a probability of correctness or proof of cause.
5. Keep provider quality, product suitability, measurement, derived summaries, and physical interpretation separate. A failure or missing QA verdict cannot be repaired by a coherent narrative or by agreement with contextual data.
6. Choose a follow-up by writing the question and its expected, weakening, and inconclusive outcomes before screening sources. Do not rank a “best next observation” numerically until ECHO has a defensible utility definition and evaluation evidence.
7. Use deterministic software for product parsing, metadata, quality checks, and numerical measurements. Any later AI assistance may organize candidate explanations or identify evidence gaps, but must cite retained evidence and remain subordinate to the scientific gates.

## Current implementation and limits

The shared investigation contract validates hypothesis fields, evidence relationships, lineage, and falsifiable follow-up designs. The browser shows evidence across hypotheses, unassessed source coverage, source dependencies, counterfactual review, and multiple sensitivity records. The retained T163 case links an authentic Sentinel-1-derived OPERA RTC-S1 diagnostic comparison to NASA optical and precipitation context; those records remain diagnostic, and the analyst-authored relationships have not been independently validated. The NISAR Iraq case displays a real bounded backscatter observation, but both products in its candidate pair have provider QA `FAIL` and no change is calculated.

These are workflow and implementation capabilities, not a scientifically validated causal engine. ECHO does not autonomously establish the physical cause, estimate calibrated confidence, or demonstrate that its reasoning outperforms a simpler method. The T163 challenge interface groups sensitivity and comparability checks while preserving their distinct scopes. The T024 interface also hands each reproducible temporal-baseline comparison back to the map, where selecting a cell exposes its retained acquisition-by-acquisition backscatter trace. A headless Firefox walkthrough verified the grouped T163 panel, the T024 challenge-to-map handoff, and the per-cell trace; the full repository suite passed 478 tests after these integrations. These checks establish software behavior, not provider QA, persistence, physical cause, or causal accuracy. See [challenge and interaction validation](../validation/adversarial-evidence-challenge-2026-11-12.md) and [temporal-baseline map validation](../validation/opera-temporal-baseline-map-2026-11-12.md).
