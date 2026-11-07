# ECHO — Dancing with the SARs

ECHO is a new, independent project exploring how to investigate Earth-surface change from Synthetic Aperture Radar (SAR) observations. It is being prepared for NASA Space Apps Challenge 2026.

The guiding question is: **what does an observed radar change support us in saying, and what remains uncertain?** A difference between observations is evidence of a change in radar response; by itself, it does not establish a physical cause.

## Project status

The initial implementation has ASF metadata discovery and a local investigation interface. A same-collection January 5/17, 2026 NISAR pair was found over the Mozambique search point. Both official QA summaries report an identification-group failure, and both products are BETA. A reusable bounded window reader has read four 100 × 100 arrays from an October PROVISIONAL scene over authenticated HTTPS; the arrays were not analyzed or compared. The interface still displays the Mozambique QA hold alongside catalog footprints and acquisition metadata. A Nepal event is under case review: its Aug 19/31 PROVISIONAL pair is a metadata candidate, but both QA summaries fail the identification-group check and no NISAR pixels have been analyzed. The app does not yet display SAR imagery, detect change, or estimate flood extent.

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
- [`requirements-nisar.lock`](requirements-nisar.lock) — pinned environment for remote NISAR inspection and tests.
- [`docs/decisions/0001-independent-project.md`](docs/decisions/0001-independent-project.md) — initial project-boundary decision.
- [`docs/decisions/0002-catalog-first-and-product-maturity.md`](docs/decisions/0002-catalog-first-and-product-maturity.md) — catalog matching and maturity boundary.
- [`docs/research/2026-11-07-first-case-review.md`](docs/research/2026-11-07-first-case-review.md) — first live NISAR data-candidate review.
- [`docs/research/2026-11-07-nepal-case-review.md`](docs/research/2026-11-07-nepal-case-review.md) — Rasuwa event evidence, a same-configuration NISAR candidate, and competing explanations for its unresolved QA failures.
- [`docs/research/2026-11-07-validated-gcov-availability.md`](docs/research/2026-11-07-validated-gcov-availability.md) — live ASF checks for the November VALIDATED GCOV release and its current catalog availability.
- [`docs/research/2026-11-07-authenticated-streaming-probe.md`](docs/research/2026-11-07-authenticated-streaming-probe.md) — bounded Earthdata-authenticated GCOV window-read evidence.
- [`data/cases/mozambique-2026/qa-review.json`](data/cases/mozambique-2026/qa-review.json) — QA checks, source hashes, inspected metadata, and the current QA hold.
- [`data/cases/nepal-2026/case-review.json`](data/cases/nepal-2026/case-review.json) — NISAR pair metadata, QA artifact hashes, and case-level evidence gates.
- [`data/cases/nepal-2026/identification-before.json`](data/cases/nepal-2026/identification-before.json), [`identification-after.json`](data/cases/nepal-2026/identification-after.json), and the `identification-x05026-*` records — authenticated HDF5 identification metadata for two processing releases; no raster arrays.
- [`data/cases/nepal-2026/catalog.json`](data/cases/nepal-2026/catalog.json) — ASF catalog metadata snapshot for the Nepal candidate; no raster pixels.
- [`docs/decisions/0003-local-investigation-interface.md`](docs/decisions/0003-local-investigation-interface.md) — local, read-only UI scope and evidence boundary.
- [`docs/decisions/0004-gcov-log-ratio-measurement.md`](docs/decisions/0004-gcov-log-ratio-measurement.md) — descriptive GCOV measurement baseline and real-data preconditions.
- [`docs/decisions/0005-bounded-gcov-window-access.md`](docs/decisions/0005-bounded-gcov-window-access.md) — authenticated range access limits, provenance, observed read amplification, and integration gates.
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

Then open <http://127.0.0.1:8765/>. The server binds to localhost by default and reads the selected catalog JSON without modifying it. The geographic view plots metadata footprints on a longitude/latitude grid; it has no basemap or SAR raster. The “challenge this finding” note is temporary browser-session input and is not saved.

To inspect the Nepal case in the same interface, select its catalog record:

```bash
.venv/bin/echo serve --case-file data/cases/nepal-2026/catalog.json
```

The interface uses the case's `case-review.json` when present and otherwise its `qa-review.json`. It selects the pair recorded by the case review, then shows those two catalog footprints and acquisition records. These are metadata candidates; the Nepal pair remains on QA hold.

The catalog search does not need Earthdata credentials and does not download HDF5 products. Product download or streaming requires a local Earthdata Login configuration. Never put Earthdata credentials in this repository or paste them into chat.

The optional `nisar` extra provides an allowlisted metadata inspector and the `read_gcov_window` Python API for bounded raster-array access. For the pinned environment, install `requirements-nisar.lock` (the lighter base environment remains in `requirements.lock`). Inspect one ASF catalog scene with:

```bash
.venv/bin/echo inspect-product \
  --catalog data/cases/nepal-2026/catalog.json \
  --scene-id NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001
```

The command uses Earthdata Login through the local netrc file, validates the catalog URL against the ASF NISAR host, and reads only an allowlist from the HDF5 identification group using bounded HTTPS byte-range requests. The Python `read_gcov_window` helper reads explicitly selected slices from allowlisted GCOV layers with sample, array-memory, and remote-range budgets. Its row and column indices must be supplied by the caller; it does not convert a geographic AOI to pixels, assess product QA, or establish grid alignment. Data access does not clear a QA hold or establish that a product is suitable for science.

The sidebar uses the user-supplied horizontal EESAR Systems logo from the provided logo pack. The source JPEG is included unchanged; CSS crops its surrounding white margin for the compact sidebar placement. ECHO remains the distinct product identity.

## Data and licensing

No radar pixels or other large data products are included. The case JSON is ASF catalog metadata only. Data attribution, redistribution terms, and the repository license remain to be assessed before adding derived or source data. The repository is private during development.
