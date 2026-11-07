# ECHO — Dancing with the SARs

ECHO is a new, independent project exploring how to investigate Earth-surface change from Synthetic Aperture Radar (SAR) observations. It is being prepared for NASA Space Apps Challenge 2026.

The guiding question is: **what does an observed radar change support us in saying, and what remains uncertain?** A difference between observations is evidence of a change in radar response; by itself, it does not establish a physical cause.

## Project status

The initial implementation has ASF metadata discovery and a local investigation interface with on-demand, metadata-only catalog search. A same-collection January 5/17, 2026 NISAR pair was found over the Mozambique search point. Both official QA summaries report an identification-group failure, and both products are BETA. A reusable bounded window reader has read four 100 × 100 arrays from an October PROVISIONAL scene over authenticated HTTPS; the arrays were not analyzed or compared. A Nepal event is under case review: its Aug 19/31 PROVISIONAL pair is a metadata candidate, but both QA summaries fail the identification-group check. A new Istanbul flood candidate has an October 9/21 PROVISIONAL NISAR metadata pair and a separate Sentinel-1-derived reference product, but both NISAR products remain on QA hold. The interface displays catalog footprints, acquisition metadata, and QA state. No NISAR pixels have been compared; the app does not yet display SAR imagery, detect change, or estimate flood extent.

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
- [`echo/nisar_access.py`](echo/nisar_access.py) — allowlisted NISAR metadata inspection and bounded authenticated GCOV window reads.
- [`echo/analysis.py`](echo/analysis.py) — QA-gated paired-window log-ratio measurement and source-to-output manifest.
- [`echo/qa.py`](echo/qa.py) — bounded ASF QA-summary retrieval, parsing, check-level disposition, and artifact hashing.
- [`echo/qa_report.py`](echo/qa_report.py) — bounded ASF QA-report retrieval, product-metadata extraction, catalog cross-checks, and versioned diagnostics; it does not set provider QA disposition.
- The local evidence panel serves retained QA-report metadata only for the selected case's scene IDs and keeps those report diagnostics separate from provider CSV QA disposition.
- [`requirements-nisar.lock`](requirements-nisar.lock) — pinned environment for remote NISAR inspection and tests.
- [`docs/decisions/0001-independent-project.md`](docs/decisions/0001-independent-project.md) — initial project-boundary decision.
- [`docs/decisions/0002-catalog-first-and-product-maturity.md`](docs/decisions/0002-catalog-first-and-product-maturity.md) — catalog matching and maturity boundary.
- [`docs/research/2026-11-07-first-case-review.md`](docs/research/2026-11-07-first-case-review.md) — first live NISAR data-candidate review.
- [`docs/research/2026-11-07-nepal-case-review.md`](docs/research/2026-11-07-nepal-case-review.md) — Rasuwa event evidence, a same-configuration NISAR candidate, and competing explanations for its unresolved QA failures.
- [`docs/research/2026-11-07-istanbul-flood-candidate.md`](docs/research/2026-11-07-istanbul-flood-candidate.md) — an October Istanbul flood candidate with a live NISAR pair, independent Sentinel-1 context, and unresolved provider QA holds.
- [`docs/research/2026-11-07-provisional-qa-sample.md`](docs/research/2026-11-07-provisional-qa-sample.md) — a bounded cross-region sample showing the same identification-check hold in four recent PROVISIONAL pairs.
- [`docs/research/2026-11-07-validated-gcov-availability.md`](docs/research/2026-11-07-validated-gcov-availability.md) — live ASF checks for the November VALIDATED GCOV release and its current catalog availability.
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

Open the local, read-only investigation interface from the repository root:

```bash
.venv/bin/echo serve
```

Then open <http://127.0.0.1:8765/>. The server binds to localhost by default and reads the selected catalog JSON without modifying it. Choose **Find observations** for a point search, or **Select Area** and drag a WGS84 rectangle on the map to search intersecting ASF footprints. Choose the date interval and GCOV maturity before submitting. Search results stay in browser memory for the current session; they are not written to the case record. The endpoint is metadata-only, capped at 250 results, and does not retrieve product pixels. The geographic view plots catalog footprints and the search location on a longitude/latitude grid. An optional NASA GIBS MODIS Terra true-color image provides optical context for the selected acquisition date; its request sends the map bounds and date to NASA. It is not NISAR data or an analysis input, and the grid remains available if the image is disabled or unavailable. The view still has no SAR raster. A no-result search is shown explicitly. The “challenge this finding” note is temporary browser-session input and is not saved.

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
