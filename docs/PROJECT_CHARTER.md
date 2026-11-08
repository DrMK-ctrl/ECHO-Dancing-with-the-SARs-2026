# ECHO project charter

**Project:** ECHO — Dancing with the SARs

**Program:** NASA International Space Apps Challenge 2026

**Status:** Pre-event implementation has begun. ASF catalog search supports BETA, PROVISIONAL, and VALIDATED GCOV collections, including point and map-drawn WGS84 rectangle searches through an on-demand metadata-only endpoint in the local interface. Metadata-level pair matching rejects same-orbit granules and overlapping acquisition intervals. A case-driven investigation interface, bounded NISAR identification-metadata inspector, allowlisted bounded GCOV array-window reader with pixel-index or WGS84-bounds selection, product CRS and pixel-center coordinates, bounded ASF QA-summary retrieval and parsing, selected-scene on-demand QA-summary inspection, and QA-gated paired-window measurement function with a provenance manifest are implemented. Live map-to-ASF area discovery, geographic selection against one authenticated PROVISIONAL product, and selected-scene provider QA retrieval have been exercised; the inspected product's provider QA is FAIL, so these checks verify access, area mapping, catalog discovery, and source inspection only. The Mozambique BETA, Nepal PROVISIONAL, and Istanbul PROVISIONAL candidates remain on QA hold; current point/date searches found no VALIDATED replacement for any of these event periods, and a separate reviewed VALIDATED product also failed its per-product identification-group check. A bounded real NISAR GCOV HH window has now been retrieved and displayed at its georeferenced position in the interactive map. Its provider QA is FAIL, so the visible layer is explicitly a QA-held diagnostic preview, not an accepted scientific result. Paired temporal measurement remains unvalidated on real NISAR arrays: no cross-date registration or accepted change result has been established.

## Purpose

Explore and build a geospatial investigation tool that helps people examine Earth-surface change in SAR observations. Its scientific foundation is the defensible analysis of radar measurements. Mapping, investigation workflow, and automated assistance should make that analysis easier to inspect and communicate.

The central distinction is between a change in measured radar response and an explanation for that change. The platform should show the evidence behind a result and make uncertainty and missing evidence visible.

## Intended investigation questions

- What observation or derived measurement changed, and over what place and time interval?
- Which product, processing steps, assumptions, and quality limitations support the comparison?
- Which physical explanations are plausible, contradicted, or still unresolved?
- What independent evidence or next observation could improve the assessment?

These questions are partly represented in a case-specific diagnostic workflow: retained measurements and acquisition dates are displayed, competing explanations link to evidence and test conditions, and open evidence needs are separated from quality prerequisites. Reviewers can now preview how the deterministic disposition changes if they hypothetically reclassify one cited evidence relationship. That preview is checksum-bound, counterfactual, and read-only; it does not verify the analyst's proposed relationship or change the retained assessment. The workflow is not yet a generalized Investigation Engine; it does not automatically judge scientific validity, rank the most informative next observation, establish causal findings, or demonstrate a QA-cleared NISAR temporal comparison.

## Scope

The project is centered on civilian SAR-based Earth observation and the NASA Space Apps Challenge 2026 challenge “Dancing with the SARs.” Potential cases may include flooding, vegetation or wetland change, wildfire effects, agriculture, ice, or ground motion. A case will be selected only after checking data suitability, provenance, reproducibility, and independent reference evidence.

The current interface connects catalog geometry, a geographic area selection, authenticated bounded retrieval of a real GCOV measurement window, and a georeferenced diagnostic raster preview. The selected scene's acquisition, source, product identity, measurement, and QA disposition are accessible in the interface. This was exercised with one QA-failed scene; the preview is diagnostic only, does not establish a valid measurement for scientific analysis, and does not yet imply general product coverage or temporal comparison. Separately, a case-specific Sentinel-1/OPERA cross-sensor assessment links measured backscatter, optical context, GPM rainfall chronology, explicit competing explanations, and evidence gaps. This workflow remains diagnostic, non-causal, and unvalidated as a general method.

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

## Initial work sequence and progress

1. Review the supplied challenge brief and verify current official submission and eligibility rules. **Partial:** the official site lists the 2026 event on November 14–15 and a submission window from November 14 at 9:00 AM through November 15 at 11:59 PM local time. The participant terms say registration is required before an event starts, while the event page says registration is available until the hackathon closes; reconcile that difference with the official platform. The terms also say submitted solutions may be posted and original content must be freely available or OSI-licensed (Apache 2.0 by default if no OSI-compliant license is specified). Therefore no submission or public release is authorized by this project charter; obtain explicit project-lead approval after reviewing the exact submission package and license implications.
2. Review authoritative NISAR product and data documentation and identify accessible candidate observations. **Partial:** an authenticated Mozambique BETA GCOV pair and Nepal PROVISIONAL GCOV pair were found and their QA artifacts reviewed; both pairs have identification-group QA failures, requiring provider reconciliation or replacement before analysis.
3. Compare established change-investigation methods and define one measurable, bounded scientific objective. **Open.**
4. Select a case only when the observations and validation evidence can support it. **Candidates only:** southern Mozambique is a data-access and QA pilot; Nepal is a PROVISIONAL candidate with an independent preliminary reference delineation but unresolved NISAR QA and redistribution terms. Neither is an evaluated science case.
5. Record architecture and evaluation decisions before implementing the end-to-end path. **Interface decisions recorded:** local, read-only case display and bounded on-demand ASF metadata search; processing architecture and evaluation method remain open.

## Open decisions

- Which challenge case has suitable, reproducible SAR observations and independent reference evidence?
- Which product family and scientific quantity fit that case?
- What baseline and evaluation measures can test whether the proposed investigation workflow adds value?
- Which scientific method and independent reference data can support the selected case?
- Which raster-processing architecture fits the validated product format and available local resources?
- Which source, data, and software licenses and attribution conditions apply?
- What work-period and pre-event development rules apply to the 2026 competition and Beirut event?

Strategic research directions and readiness gates are recorded in [`PROJECT_DIRECTION.md`](PROJECT_DIRECTION.md). These do not change the current implementation scope until their evidence and dependency gates are met.

## References to verify

- NASA Space Apps Challenge 2026, “Dancing with the SARs”: <https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/>
- NASA NISAR mission: <https://science.nasa.gov/mission/nisar/>
- NASA NISAR data: <https://science.nasa.gov/mission/nisar/data/>
- NASA NISAR sample data: <https://science.nasa.gov/mission/nisar/sample-data/>
- Alaska Satellite Facility NISAR documentation: <https://nisar-docs.asf.alaska.edu/>

The challenge page and NASA NISAR links are starting points supplied in the project brief. The challenge page's full statement, judging criteria, and the current technical NISAR product documentation still need direct review.

## Competition rules checked on 2026-11-08

- The event page says registration for Global Judging may continue until the hackathon closes, while the participant terms require registration before the event starts. This contradiction remains unresolved; plan to meet the earlier deadline and verify the registered state in the participant account.
- The participant terms say posted solutions are downloadable, original challenge content must be freely available or OSI-licensed, and Apache 2.0 applies if no OSI-compliant license is specified. They also require third-party license documentation and source citation. These terms do not authorize publication: keep the repository private and obtain explicit approval for the exact submission package and release terms.
- The project lead supplied the Beirut presentation format and Slack documentation requirements; these are recorded separately as local organizer guidance and were not independently confirmed on a public Beirut 2026 page.
- The challenge detail page and current Global Judging criteria remain unverified because the official detail page could not be retrieved in this check. Do not substitute third-party summaries for the official brief.

See [competition rules validation](validation/space-apps-competition-rules-2026-11-08.md) for sources, boundaries, and outstanding checks.

Sources: [NASA Space Apps 2026](https://www.spaceappschallenge.org/2026/) · [2026 Participant Terms and Conditions](https://www.spaceappschallenge.org/legal/) · [Dancing with the SARs challenge page](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/)
