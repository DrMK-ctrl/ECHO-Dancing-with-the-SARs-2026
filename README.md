# ECHO — Dancing with the SARs

ECHO is a new, independent project exploring how to investigate Earth-surface change from Synthetic Aperture Radar (SAR) observations. It is being prepared for NASA Space Apps Challenge 2026.

The guiding question is: **what does an observed radar change support us in saying, and what remains uncertain?** A difference between observations is evidence of a change in radar response; by itself, it does not establish a physical cause.

## Project status

The implementation has ASF metadata discovery and a local investigation interface with on-demand catalog search. GCOV searches follow ASF CMR result pages up to 1,000 records and explicitly mark a result set that reaches that cap as potentially incomplete. The interface timelines returned observations, offers metadata-compatible pair candidates, and connects selection to source metadata and map footprints. The map can be panned by dragging or keyboard arrow keys, reset to its search extent, and used to draw a WGS84 search rectangle; catalog results do not establish complete pixel coverage. A selected GCOV scene and AOI can request a bounded, authenticated backscatter window, choose an available real-valued diagonal polarization layer and A/B frequency, display geolocated product measurements on the map, inspect a pixel's value and quality codes, and export a checksummed source and processing record. Provider QA remains explicit; QA-failed previews are diagnostic only. This preview is not temporal change analysis. A QA-first bounded pair-analysis API and workspace control now connect metadata pair selection and a WGS84 AOI to both product QA checks, bounded windows, and the existing grid/common-validity-gated analyzer. A non-PASS disposition returns source QA records and stops before measurement reads. A QA-PASS response can render a descriptive geolocated log-ratio field with a display-only stretch, source links, pixel inspection, and a reproduction record; the successful measurement path has synthetic integration coverage only. The real Nepal candidate currently returns `QA_HELD` for both products, so the map correctly shows no comparison raster. A bounded, read-only Bhoonidhi client also supports metadata search for online NISAR S-SAR GCOV items with locally prompted credentials; no S-SAR product has yet been retrieved or validated. A November 7 screen of 13 unique Nepal-area GCOV candidate granules found provider identification-group failures on all 13. A separate bounded screen discovered PROVISIONAL GUNW products at five regions, and all five sampled QA summaries report the same identification-group failure. A product-specific bounded GUNW reader retrieves authenticated phase, coherence, connected-component, mask, and optional ionosphere windows with checksummed provenance. The first Istanbul AOI had no supported subswath pixels; a second window was water-dominated with low coherence. A nine-product Tehran frame-70 GUNW sequence includes one approximately 24-day pair spanning a NASA-documented NISAR acquisition outage; all nine product QA summaries remain `FAIL`. Three same-AOI pair windows select the same 154 pixel centers, with pair-specific mean coherence of 0.761, 0.797, and 0.802. All three retain provider QA `FAIL` and the ionosphere-interpolated mask flag on all centers; phase was not compared or corrected, and no displacement or event interpretation was made. A November 7 global VALIDATED-GCOV screen returned 993 unique scenes across paginated daily windows, with no result-cap truncation and one metadata-compatible 12-day pair. Both products in that pair report provider identification-group `FAIL`, so ECHO held it before reading measurement arrays. The paired gamma0 log-ratio routine has synthetic integration coverage, but no real NISAR pair has passed QA, grid-alignment, and common-valid-pixel gates or been analyzed; no change finding or flood extent is available.

The newest VALIDATED scene returned by a focused 2026-10-30–2026-11-07 refresh was read through the generic GCOV window path. ECHO now reads and records the dataset's own HDF5 quality attributes and decodes the UInt16 polarization-validity bit field for the selected diagonal channel. For the inspected HHHH AOI, `inputDataExceptionMask=768` means the product's HH and HV focused-data bits are set; 10,562 of 10,648 centers pass the documented display mask. The preview remains explicitly `QA_HELD_DIAGNOSTIC_PREVIEW` because the canonical ASF summary still reports `FAIL` for identification checks. The [diagnostic window review](docs/research/2026-11-07-validated-gcov-diagnostic-window.md) retains both the initial zero-pixel interpretation and the product-attribute reevaluation; this single-scene view is not an accepted change analysis.

## Working principles

- Keep measured observations, derived quantities, interpretations, and hypotheses distinguishable.
- Select methods according to the documented contents and limitations of each data product.
- Preserve source, processing, configuration, and validation provenance for analytical results.
- Compare explanations and report inconclusive outcomes when evidence is insufficient.
- Evaluate any added analytical complexity against an appropriate baseline.
- Keep the application focused on civilian Earth observation and the selected SAR challenge.

## Planned investigation path

The project will verify challenge requirements, data access, product semantics, scientific references, and applicable submission rules before selecting an analytical method. Strategic directions and their research gates are recorded in [`docs/PROJECT_DIRECTION.md`](docs/PROJECT_DIRECTION.md); proposed capabilities there are not implemented features or architecture decisions.

## Repository guide

- [`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md) — scope, evidence standards, and initial open questions.
- [`docs/PROJECT_DIRECTION.md`](docs/PROJECT_DIRECTION.md) — strategic philosophy, future investigation-engine ideas, and research/readiness gates.
- [`echo/bhoonidhi.py`](echo/bhoonidhi.py) — bounded, provenance-preserving metadata search for online NISAR S-SAR GCOV products; tokens remain in memory.
- [`echo/nisar_access.py`](echo/nisar_access.py) — allowlisted NISAR metadata inspection and bounded authenticated GCOV window reads.
- [`echo/gunw_access.py`](echo/gunw_access.py) — product-specific bounded GUNW window reads, mask-field decoding, and layer/coordinate checksums; no phase correction or displacement interpretation.
- [`echo/opera_rtc.py`](echo/opera_rtc.py) and [`echo/opera_rtc_access.py`](echo/opera_rtc_access.py) — experimental OPERA RTC-S1 product-mask decoding, exact-grid-gated gamma-zero pair measurement, and capped in-memory reads of complete per-burst COG assets with bounded AOI output arrays. These paths have fixture-based coverage, but authenticated asset retrieval, real-pixel comparison, provenance packaging, and interface integration remain unverified; no Sentinel-1 change result is claimed.
- [`echo/analysis.py`](echo/analysis.py) — QA-gated paired-window log-ratio measurement and source-to-output manifest.
- [`echo/qa.py`](echo/qa.py) — bounded ASF QA-summary retrieval, parsing, check-level disposition, and artifact hashing.
- [`echo/qa_report.py`](echo/qa_report.py) — bounded ASF GCOV/GUNW QA-report retrieval, product-metadata extraction, catalog cross-checks, and versioned diagnostics; it does not set provider QA disposition.
- The local evidence panel can retrieve and inspect the selected catalog scene's bounded provider QA CSV on demand. Retained QA-report metadata remains separate from provider CSV disposition; session-fetched summaries are not written to case files.
- [`requirements-nisar.lock`](requirements-nisar.lock) — pinned environment for remote NISAR inspection and tests.
- [`docs/decisions/0001-independent-project.md`](docs/decisions/0001-independent-project.md) — initial project-boundary decision.
- [`docs/decisions/0002-catalog-first-and-product-maturity.md`](docs/decisions/0002-catalog-first-and-product-maturity.md) — catalog matching and maturity boundary.
- [`docs/decisions/0014-selectable-catalog-chronology.md`](docs/decisions/0014-selectable-catalog-chronology.md) — selectable chronology across records returned by a query.
- [`docs/decisions/0015-on-demand-provider-qa-inspection.md`](docs/decisions/0015-on-demand-provider-qa-inspection.md) — bounded selected-scene ASF QA summary retrieval and source inspection.
- [`docs/decisions/0016-bounded-bhoonidhi-ssar-discovery.md`](docs/decisions/0016-bounded-bhoonidhi-ssar-discovery.md) — separate, authenticated, read-only NISAR S-SAR GCOV catalog discovery.
- [`docs/validation/observation-timeline-2026-11-07.md`](docs/validation/observation-timeline-2026-11-07.md) — browser interaction, missing-time, and responsive-layout evidence for the timeline.
- [`docs/validation/comparison-candidate-selector-2026-11-07.md`](docs/validation/comparison-candidate-selector-2026-11-07.md) — browser evidence for choosing among catalog-screened temporal pairs; no measurement is produced.
- [`docs/validation/on-demand-provider-qa-2026-11-07.md`](docs/validation/on-demand-provider-qa-2026-11-07.md) — endpoint and live browser evidence for selected-scene provider QA inspection.
- [`docs/research/2026-11-07-first-case-review.md`](docs/research/2026-11-07-first-case-review.md) — first live NISAR data-candidate review.
- [`docs/research/2026-11-07-nepal-case-review.md`](docs/research/2026-11-07-nepal-case-review.md) — Rasuwa event evidence, a same-configuration NISAR candidate, and competing explanations for its unresolved QA failures.
- [`data/research/kathmandu-candidate-qa-screen-2026-11-07.json`](data/research/kathmandu-candidate-qa-screen-2026-11-07.json) — authenticated QA-summary dispositions, checks, and artifact hashes for 13 distinct candidate granules; all remain on provider QA hold.
- [`tools/research/screen_nisar_crid_reprocessing_qa.py`](tools/research/screen_nisar_crid_reprocessing_qa.py) and [`data/research/nepal-alternate-crid-qa-2026-11-07.json`](data/research/nepal-alternate-crid-qa-2026-11-07.json) — reproducible ASF QA-summary/report screen for the alternate X05026 Nepal pair; both products remain QA `FAIL`, with report metadata, artifact hashes, and source-rule cross-checks retained.
- [`docs/research/2026-11-07-nepal-candidate-qa-screen.md`](docs/research/2026-11-07-nepal-candidate-qa-screen.md) — screening method, findings, and limits; QA metadata only, no pixel analysis.
- [`docs/research/2026-11-07-istanbul-flood-candidate.md`](docs/research/2026-11-07-istanbul-flood-candidate.md) — an October Istanbul flood candidate with a live NISAR pair, independent Sentinel-1 context, and unresolved provider QA holds.
- [`docs/research/2026-11-07-provisional-qa-sample.md`](docs/research/2026-11-07-provisional-qa-sample.md) — a bounded cross-region sample showing the same identification-check hold in four recent PROVISIONAL pairs.
- [`docs/research/2026-11-07-validated-gcov-availability.md`](docs/research/2026-11-07-validated-gcov-availability.md) — live ASF checks for the November VALIDATED GCOV release and its current catalog availability.
- [`docs/research/2026-11-07-validated-product-qa-report-review.md`](docs/research/2026-11-07-validated-product-qa-report-review.md) — product QA summary, report, and statistics artifacts reviewed without reading GCOV measurement arrays.
- [`tools/research/screen_opera_rtc_series.py`](tools/research/screen_opera_rtc_series.py) and [`data/research/opera-rtc-s1-brazil-flood-screen-2026-11-07.json`](data/research/opera-rtc-s1-brazil-flood-screen-2026-11-07.json) — repeat-burst OPERA RTC-S1 candidates for the 2024 Rio Grande do Sul floods; metadata only, with Sentinel-1 provenance kept separate from NISAR.
- [`tools/research/screen_validated_gcov_time_series.py`](tools/research/screen_validated_gcov_time_series.py) and [`data/research/validated-gcov-global-time-series-2026-11-07.json`](data/research/validated-gcov-global-time-series-2026-11-07.json) — reproducible global daily metadata screen and orbit-aware pair results; one query day reached its result cap, and no pixels were read.
- [`docs/research/2026-11-07-nisar-ssar-bhoonidhi-feasibility.md`](docs/research/2026-11-07-nisar-ssar-bhoonidhi-feasibility.md) — official-source feasibility review for a separate NISAR S-SAR GCOV provider path; no S-SAR product has yet been retrieved or validated.
- [`docs/research/2026-11-07-nisar-gunw-feasibility.md`](docs/research/2026-11-07-nisar-gunw-feasibility.md) — bounded NISAR GUNW discovery, NASA expert guidance, product-specific metadata review, and the live pixel-window result with its retained provider-QA hold.
- [`tools/research/inspect_gunw_product_metadata.py`](tools/research/inspect_gunw_product_metadata.py) and [`data/research/gunw-p05023-product-metadata-review.json`](data/research/gunw-p05023-product-metadata-review.json) — reproducible bounded review of one PROVISIONAL GUNW QA report and selected identification metadata; no measurement arrays.
- [`tools/research/inspect_gunw_window.py`](tools/research/inspect_gunw_window.py) and [`data/research/gunw-istanbul-ayazaga-pixel-window-2026-11-07.json`](data/research/gunw-istanbul-ayazaga-pixel-window-2026-11-07.json) — reproducible authenticated GUNW AOI pixel access and mask characterization; no scientific change result.
- [`data/research/gunw-istanbul-footprint-interior-pixel-window-2026-11-07.json`](data/research/gunw-istanbul-footprint-interior-pixel-window-2026-11-07.json) and [`data/research/gunw-tehran-footprint-interior-with-ionosphere-pixel-window-2026-11-07.json`](data/research/gunw-tehran-footprint-interior-with-ionosphere-pixel-window-2026-11-07.json) — additional water and land-window QA characterization, including ionosphere layers; both preserve provider `FAIL` and make no displacement finding.
- [`data/research/validated-qa-sample-2026-11-07.json`](data/research/validated-qa-sample-2026-11-07.json) — provenance and per-check QA evidence for four current VALIDATED products on distinct paths; all remain on identification-check hold.
- [`docs/research/2026-11-07-authenticated-streaming-probe.md`](docs/research/2026-11-07-authenticated-streaming-probe.md) — bounded Earthdata-authenticated GCOV window-read evidence.
- [`data/cases/mozambique-2026/qa-review.json`](data/cases/mozambique-2026/qa-review.json) — QA checks, source hashes, inspected metadata, and the current QA hold.
- [`data/cases/nepal-2026/case-review.json`](data/cases/nepal-2026/case-review.json) — NISAR pair metadata, QA artifact hashes, and case-level evidence gates.
- [`data/cases/nepal-2026/identification-before.json`](data/cases/nepal-2026/identification-before.json), [`identification-after.json`](data/cases/nepal-2026/identification-after.json), and the `identification-x05026-*` records — authenticated HDF5 identification metadata for two processing releases; no raster arrays.
- [`data/cases/nepal-2026/catalog.json`](data/cases/nepal-2026/catalog.json) — ASF catalog metadata snapshot for the Nepal candidate; no raster pixels.
- [`data/cases/istanbul-2026/case-review.json`](data/cases/istanbul-2026/case-review.json) — Istanbul candidate review; both NISAR products remain on QA hold and no raster arrays were analyzed.
- [`docs/decisions/0003-local-investigation-interface.md`](docs/decisions/0003-local-investigation-interface.md) — local, read-only UI scope and evidence boundary.
- [`docs/decisions/0004-gcov-log-ratio-measurement.md`](docs/decisions/0004-gcov-log-ratio-measurement.md) — descriptive GCOV measurement baseline and real-data preconditions.
- [`docs/decisions/0005-bounded-gcov-window-access.md`](docs/decisions/0005-bounded-gcov-window-access.md) — authenticated range access limits, provenance, observed read amplification, and integration gates.
- [`docs/decisions/0006-gcov-grid-metadata.md`](docs/decisions/0006-gcov-grid-metadata.md) — projection and pixel-center coordinates retained with each bounded array window.
- [`docs/decisions/0007-provenance-gated-pair-measurement.md`](docs/decisions/0007-provenance-gated-pair-measurement.md) — paired-window analysis gates, quality summaries, and checksummed lineage.
- [`docs/decisions/0008-validated-catalog-and-orbit-aware-pairing.md`](docs/decisions/0008-validated-catalog-and-orbit-aware-pairing.md) — VALIDATED collection support and temporal acquisition safeguards.
- [`docs/decisions/0017-interactive-gcov-single-scene-preview.md`](docs/decisions/0017-interactive-gcov-single-scene-preview.md) — bounded real-pixel map preview, QA boundary, layer selection, and page-aware catalog cap.
- [`docs/decisions/0018-qa-first-paired-gcov-analysis-route.md`](docs/decisions/0018-qa-first-paired-gcov-analysis-route.md) — bounded pair-analysis endpoint, QA-first execution order, and map-integration gates.
- [`docs/decisions/0009-ingest-provider-qa-summaries.md`](docs/decisions/0009-ingest-provider-qa-summaries.md) — bounded QA-summary retrieval, row-level dispositions, and artifact checksums.
- [`docs/decisions/0010-on-demand-catalog-discovery.md`](docs/decisions/0010-on-demand-catalog-discovery.md) — bounded, read-only ASF catalog searches from the investigation interface.
- [`docs/decisions/0012-geographic-gcov-window-selection.md`](docs/decisions/0012-geographic-gcov-window-selection.md) — bounded WGS84 AOI mapping, exact pixel-center masking, and its QA boundary.
- [`docs/decisions/0013-map-drawn-aoi-catalog-search.md`](docs/decisions/0013-map-drawn-aoi-catalog-search.md) — map-drawn WGS84 rectangles connected to ASF metadata search.
- [`docs/validation/area-catalog-search-2026-11-07.md`](docs/validation/area-catalog-search-2026-11-07.md) — Firefox interaction and live AOI catalog-query evidence.
- [`docs/validation/area-catalog-search-2026-11-07.png`](docs/validation/area-catalog-search-2026-11-07.png) — captured map with the selected AOI and returned ASF footprints.
- [`data/research/kathmandu-aoi-catalog-query-2026-11-07.json`](data/research/kathmandu-aoi-catalog-query-2026-11-07.json) — reproducible live AOI query and catalog candidates; no pixels.
- [`docs/validation/geographic-window-access-2026-11-07.md`](docs/validation/geographic-window-access-2026-11-07.md) — authenticated real-product geographic access record; no pixel analysis.
- [`data/research/geographic-window-access-2026-11-07.json`](data/research/geographic-window-access-2026-11-07.json) — machine-readable selection, source QA, and access provenance.
- [`echo/science.py`](echo/science.py) — pure-array gamma0 log-ratio and regional summary primitives; no product reader or detector.
- [`docs/validation/interface-2026-11-07.md`](docs/validation/interface-2026-11-07.md) — browser smoke-check evidence and validation limits.
- [`data/cases/mozambique-2026/catalog.json`](data/cases/mozambique-2026/catalog.json) — a dated ASF catalog metadata snapshot; contains no radar pixels.

## Development

Python 3.11 or newer is required. Python 3.14.4 was used for the initial implementation.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pytest
```

Run a metadata-only search around the Mozambique case:

```bash
.venv/bin/echo catalog \
  --longitude 33.5 --latitude -24.5 \
  --start 2026-01-01 --end 2026-01-31 \
  --maturity BETA \
  --output data/cases/mozambique-2026/catalog.json
```

For a read-only search of online ISRO Bhoonidhi NISAR S-SAR GCOV catalog items, use a registered Bhoonidhi account. The command prompts for the account ID and a non-echoed password, uses the short-lived token in memory, and can write a checksummed provenance envelope around the raw STAC response:

```bash
.venv/bin/echo bhoonidhi-search \
  --bbox 76.8 28.4 77.4 28.9 \
  --start 2026-07-01T00:00:00Z --end 2026-08-01T00:00:00Z \
  --output /tmp/echo-bhoonidhi-catalog.json
```

The query requests only `NISAR_SSAR_GCOV` items marked online, with a maximum of 500 results. It does not download products, evaluate provider QA, or authorize measurement. See the [S-SAR feasibility review](docs/research/2026-11-07-nisar-ssar-bhoonidhi-feasibility.md) for product and access limitations.

Open the local, read-only investigation interface from the repository root:

```bash
.venv/bin/echo serve
```

Then open <http://127.0.0.1:8765/>. The server binds to localhost by default and reads the selected catalog JSON without modifying it. Choose **Find observations** for a point search, or **Select Area** and drag a WGS84 rectangle on the map to search intersecting ASF footprints. Choose the date interval and GCOV maturity before submitting. Search results stay in browser memory for the current session; they are not written to the case record. Catalog search follows CMR pages up to 1,000 results and marks a result set potentially incomplete if it reaches that cap. The geographic view plots catalog footprints and the search location on a longitude/latitude grid. An optional NASA GIBS MODIS Terra true-color image provides optical context for the selected acquisition date; its request sends the map bounds and date to NASA. It is not NISAR data or an analysis input, and the grid remains available if the image is disabled or unavailable. A no-result search is shown explicitly. The “challenge this finding” note is temporary browser-session input and is not saved.

For a GCOV catalog result, select a WGS84 area and choose a catalog-supported polarization layer and frequency, then choose **Load Backscatter** for an authenticated bounded read of that diagonal gamma-zero layer and its product mask, number of looks, and exception mask. The map colors actual product values; it is not a browse image. ECHO obtains the provider QA summary first, records its checksum and source, grid, range-read, selection, and array provenance, and can export the complete preview record. A preview with provider QA `FAIL` is explicitly labeled **QA-held diagnostic preview** and is not promoted to comparison, event detection, or physical interpretation. This single-observation path establishes data access and rendering, not temporal change. Remote reads are capped at 65,536 pixels and reject unsupported layers or invalid geographic bounds. The catalog interface follows ASF's 250-product CMR pages up to a 1,000-result application cap; reaching the cap is surfaced as potentially incomplete, and the user can narrow the date or area query.

Select an observation and choose **Fetch QA** to retrieve its canonical ASF QA-summary CSV through the configured local Earthdata Login. The interface shows each provider check with retrieval provenance and a SHA-256 checksum. **Export Source Record** downloads a JSON evidence record joining the selected catalog query and feature with the provider response. The request is limited to a supported ASF NISAR GCOV product and the CSV reader is capped at 64 KiB. Provider QA remains distinct from ECHO's scientific suitability gates; a pass does not authorize measurement, and the QA request does not read HDF5 metadata or radar arrays.

The interface acknowledges NASA GIBS imagery as requested in the [GIBS data use guidance](https://nasa-gibs.github.io/gibs-api-docs/). See [Decision 0011](docs/decisions/0011-nasa-gibs-contextual-basemap.md) for the layer boundary and fallback behavior.

To inspect the Nepal case in the same interface, select its catalog record:

```bash
.venv/bin/echo serve --case-file data/cases/nepal-2026/catalog.json
```

The interface uses the case's `case-review.json` when present and otherwise its `qa-review.json`. It selects the pair recorded by the case review, then shows those two catalog footprints and acquisition records. These are metadata candidates; the Nepal pair remains on QA hold.

Catalog discovery does not need Earthdata credentials and does not download HDF5 products. Product download or streaming requires a local Earthdata Login configuration. Never put Earthdata credentials in this repository or paste them into chat.

The optional `nisar` extra provides an allowlisted metadata inspector and the `read_gcov_window` Python API for bounded raster-array access. For the pinned environment, install `requirements-nisar.lock` (the lighter base environment remains in `requirements.lock`). Inspect one ASF catalog scene with:

```bash
.venv/bin/echo inspect-product \
  --catalog data/cases/nepal-2026/catalog.json \
  --scene-id NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001
```

The command uses Earthdata Login through the local netrc file, validates the catalog URL against the ASF NISAR host, and reads only an allowlist from the HDF5 identification group using bounded HTTPS byte-range requests. The Python `read_gcov_window` helper accepts either explicit row/column slices or a WGS84 bounding box. Geographic selection reads bounded full coordinate vectors, maps the rectangle to a projected GCOV window, and returns a pixel-center mask for the exact requested area. Sample, coordinate-array, raster-memory, and remote-range budgets apply. The reader does not assess product QA or establish cross-date grid alignment. Data access does not clear a QA hold or establish that a product is suitable for science.

Inspect the matching ASF QA report and its versioned metadata cross-check with:

```bash
.venv/bin/echo inspect-qa-report \
  --catalog data/cases/istanbul-2026/catalog.json \
  --scene-id NISAR_L2_PR_GCOV_033_137_D_068_2005_DHDH_A_20261021T170432_20261021T170507_P05023_N_F_J_001
```

This command retrieves only the bounded QA PDF, records its source and checksum, verifies the report scene ID against ASF catalog metadata, and compares orbit, track, and frame values. Its source-code cross-check is diagnostic only; the PDF does not set QA disposition. The separate provider CSV remains `FAIL` for this scene, and the analysis hold remains active.

The sidebar uses the user-supplied horizontal EESAR Systems logo from the provided logo pack. The source JPEG is included unchanged; CSS crops its surrounding white margin for the compact sidebar placement. ECHO remains the distinct product identity.

## Data and licensing

No radar pixels or other large data products are included. The case JSON is ASF catalog metadata only. Data attribution, redistribution terms, and the repository license remain to be assessed before adding derived or source data. The repository is private during development.
