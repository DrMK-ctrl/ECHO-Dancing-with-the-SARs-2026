# ECHO project charter

**Project:** ECHO — Dancing with the SARs

**Program:** NASA International Space Apps Challenge 2026

**Status:** Pre-event implementation has begun. ASF catalog search and metadata-level GCOV pair matching are implemented. No radar pixels have been processed, and no scientific result or validation is claimed.

## Purpose

Explore and build a geospatial investigation tool that helps people examine Earth-surface change in SAR observations. Its scientific foundation is the defensible analysis of radar measurements. Mapping, investigation workflow, and automated assistance should make that analysis easier to inspect and communicate.

The central distinction is between a change in measured radar response and an explanation for that change. The platform should show the evidence behind a result and make uncertainty and missing evidence visible.

## Intended investigation questions

- What observation or derived measurement changed, and over what place and time interval?
- Which product, processing steps, assumptions, and quality limitations support the comparison?
- Which physical explanations are plausible, contradicted, or still unresolved?
- What independent evidence or next observation could improve the assessment?

These are project goals, not implemented capabilities.

## Scope

The project is centered on civilian SAR-based Earth observation and the NASA Space Apps Challenge 2026 challenge “Dancing with the SARs.” Potential cases may include flooding, vegetation or wetland change, wildfire effects, agriculture, ice, or ground motion. A case will be selected only after checking data suitability, provenance, reproducibility, and independent reference evidence.

The eventual system may combine scientific processing, geospatial presentation, and investigation assistance. The concrete architecture and methods remain open until challenge requirements and candidate data products are reviewed.

## Scientific and evidence rules

1. Label evidence as observed, computed, interpreted, hypothesized, or unverified where that distinction affects a claim.
2. Do not infer physical cause from visual difference alone.
3. Do not claim calibrated probability, accuracy, novelty, or performance without an evaluation that supports that exact claim.
4. Use only analyses supported by a product's documented measurements. Do not derive interferometric quantities from products that do not preserve the required phase information.
5. Record data identifiers and versions, source links, processing configuration, software version, and validation references for each reproducible case.
6. Treat missing coverage, incompatible products, and inconclusive results as reportable outcomes.
7. Compare proposed analytical complexity with a suitable simpler baseline and document failure modes.
8. Keep synthetic fixtures clearly labeled and separate from real observational evidence.

## Project boundaries

- This is an independent project with a clean technical foundation and its own repository and history.
- The separate passive-RF EESAR application is outside this project's code and architecture.
- No operational targeting, military asset tracking, or tactical intelligence capability is in scope.
- No paid services, purchases, or public release are authorized by this charter.
- Repository visibility remains private unless the project lead explicitly authorizes a change.
- No third-party data or source code is vendored. Runtime dependencies are declared in `pyproject.toml` and pinned in `requirements.lock`.

## Initial work sequence

1. Verify the official challenge brief, judging and submission rules, and relevant 2026 eligibility and attribution requirements.
2. Review authoritative NISAR product and data documentation and identify accessible candidate observations.
3. Compare established change-investigation methods and define one measurable, bounded scientific objective.
4. Select a case only when the observations and validation evidence can support it.
5. Record architecture and evaluation decisions before implementing the end-to-end path.

## Open decisions

- Which challenge case has suitable, reproducible SAR observations and independent reference evidence?
- Which product family and scientific quantity fit that case?
- What baseline and evaluation measures can test whether the proposed investigation workflow adds value?
- Which runtime and interface architecture best fits the selected data and judging demonstration?
- Which source, data, and software licenses and attribution conditions apply?
- What work-period and pre-event development rules apply to the 2026 competition and Beirut event?

## References to verify

- NASA Space Apps Challenge 2026, “Dancing with the SARs”: <https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/>
- NASA NISAR mission: <https://science.nasa.gov/mission/nisar/>
- NASA NISAR data: <https://science.nasa.gov/mission/nisar/data/>
- NASA NISAR sample data: <https://science.nasa.gov/mission/nisar/sample-data/>
- Alaska Satellite Facility NISAR documentation: <https://nisar-docs.asf.alaska.edu/>

These links are starting points supplied in the project brief. Their current contents and applicability have not yet been reviewed in this repository.
