# ECHO — Dancing with the SARs

ECHO is a new, independent project exploring how to investigate Earth-surface change from Synthetic Aperture Radar (SAR) observations. It is being prepared for NASA Space Apps Challenge 2026.

The guiding question is: **what does an observed radar change support us in saying, and what remains uncertain?** A difference between observations is evidence of a change in radar response; by itself, it does not establish a physical cause.

## Project status

The initial implementation has ASF metadata discovery and a local investigation interface. A same-collection January 5/17, 2026 NISAR pair was found over the Mozambique search point. Both official QA summaries report an identification-group failure, and both products are BETA. The interface displays that QA hold alongside catalog footprints and acquisition metadata. No raster values have been analyzed, so it does not display SAR imagery, detect change, or estimate flood extent.

## Working principles

- Keep measured observations, derived quantities, interpretations, and hypotheses distinguishable.
- Select methods according to the documented contents and limitations of each data product.
- Preserve source, processing, configuration, and validation provenance for analytical results.
- Compare explanations and report inconclusive outcomes when evidence is insufficient.
- Evaluate any added analytical complexity against an appropriate baseline.
- Keep the application focused on civilian Earth observation and the selected SAR challenge.

## Planned investigation path

The project will first verify the challenge requirements, data access, product semantics, scientific references, and applicable submission rules. The initial technical direction and validation plan will be recorded after that review. No architectural or scientific capability is claimed by this outline.

## Repository guide

- [`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md) — scope, evidence standards, and initial open questions.
- [`docs/decisions/0001-independent-project.md`](docs/decisions/0001-independent-project.md) — initial project-boundary decision.
- [`docs/decisions/0002-catalog-first-and-product-maturity.md`](docs/decisions/0002-catalog-first-and-product-maturity.md) — catalog matching and maturity boundary.
- [`docs/research/2026-11-07-first-case-review.md`](docs/research/2026-11-07-first-case-review.md) — first live NISAR data-candidate review.
- [`data/cases/mozambique-2026/qa-review.json`](data/cases/mozambique-2026/qa-review.json) — QA checks, source hashes, inspected metadata, and the current QA hold.
- [`docs/decisions/0003-local-investigation-interface.md`](docs/decisions/0003-local-investigation-interface.md) — local, read-only UI scope and evidence boundary.
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

The catalog search does not need Earthdata credentials and does not download HDF5 products. Product download or streaming requires a local Earthdata Login configuration. Never put Earthdata credentials in this repository or paste them into chat.

The sidebar uses the user-supplied horizontal EESAR Systems logo from the provided logo pack. The source JPEG is included unchanged; CSS crops its surrounding white margin for the compact sidebar placement. ECHO remains the distinct product identity.

## Data and licensing

No radar pixels or other large data products are included. The case JSON is ASF catalog metadata only. Data attribution, redistribution terms, and the repository license remain to be assessed before adding derived or source data. The repository is private during development.
