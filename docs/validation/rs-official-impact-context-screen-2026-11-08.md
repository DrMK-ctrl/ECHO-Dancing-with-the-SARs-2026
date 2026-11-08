# Rio Grande do Sul official affected-area source screen

**Result:** Authoritative event context found; it does not independently test the T163 SAR explanation.

## Reproduction scope

- Queried IEDE-RS layer `0` (`area_diretamente_atingida_2024`) for the T163 WGS84 AOI `[-51.24, -30.04, -51.23, -30.03]`.
- One source polygon was returned, identified as Porto Alegre, `ADA 03/09/2024`.
- Clipped that polygon to the AOI and calculated overlap in EPSG:6933: 703,662.9 m² of 1,069,204.2 m² (65.81%). The source polygon does not contain the AOI center.
- No rasterization, resampling, water classification, or SAR measurement was performed.

The query response SHA-256 is retained in the linked JSON record. The same record contains the clipped geometry, the source query, processing method and software versions, and its scientific role and limitations.

## Scientific assessment

The service description says the affected-area layer aggregates Planet-derived mapping and partner contributions and is validated with Planet, Sentinel, DEM, and hydrography. It does not expose per-feature observation dates or component-source lineage. CEMADEN's event mapping is model-based and uses water-level gauges, HEC-RAS 2D/HAND, terrain, GloFAS flows, and Planet imagery.

This source supports only the statement that the AOI partly overlaps a later, aggregated official event-impact polygon. It cannot establish floodwater at either RTC-S1 acquisition time or validate the radar measurement. It was therefore excluded from the T163 hypothesis evidence set and does not alter the unresolved assessment or provider-QA status.

See [Decision 0038](../decisions/0038-classify-rs-affected-area-as-event-context.md) and the [retained source screen](../../data/research/rio-grande-do-sul-t163-official-impact-context-screen-2026-11-08.json).
