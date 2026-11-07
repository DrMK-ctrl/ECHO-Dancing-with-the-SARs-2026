# ECHO — Dancing with the SARs

ECHO is a new, independent project exploring how to investigate Earth-surface change from Synthetic Aperture Radar (SAR) observations. It is being prepared for NASA Space Apps Challenge 2026.

The guiding question is: **what does an observed radar change support us in saying, and what remains uncertain?** A difference between observations is evidence of a change in radar response; by itself, it does not establish a physical cause.

## Project status

This repository currently contains the project charter and development boundaries only. No SAR processing, change detection, geospatial interface, automated analysis, or validated case study has been implemented here yet.

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

## Development

There is no runnable application or dependency environment in this initial milestone. Setup instructions will be added with the first implementation and kept aligned with the actual code.

## Data and licensing

No external datasets or third-party code are included. Data attribution, redistribution terms, and the repository license remain to be assessed before those materials are added. The repository is private during development.
