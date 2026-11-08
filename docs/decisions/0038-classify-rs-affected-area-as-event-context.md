# Decision 0038: Keep the state affected-area layer as event context

**Date:** 2026-11-08
**Status:** Accepted for source classification; excluded from the T163 causal assessment

## Context

The T163-349925 AOI is part of a Rio Grande do Sul flood investigation. A Rio Grande do Sul state geospatial layer titled `area_diretamente_atingida_2024` intersects the AOI and initially appeared to offer an external reference for the water-change hypothesis.

## Evidence reviewed

The state service describes an aggregated directly affected area assembled from a Planet-derived layer and partner contributions, including ALM, CEMADEN, INPE, FURG, and UFRGS. Its description says the combined area is validated using Planet and Sentinel imagery, elevation, and hydrography. The returned feature is versioned `ADA 03/09/2024`; its attributes contain no feature-level observation interval or source-component lineage.

The CEMADEN technical note for the April–May 2024 event describes modeled inundation maps based on gauge water levels, HEC-RAS 2D and HAND, with Copernicus DEM, ANA gauge data, GloFAS flows, and Planet imagery as inputs. This is authoritative event-impact context, but the documented products do not provide a dated direct water observation for the T163 AOI at either SAR acquisition.

The state polygon was intersected with the T163 WGS84 AOI and measured in EPSG:6933. It overlaps 703,662.9 m², or 65.81% of the AOI, while excluding the AOI center. This describes overlap with the mapped affected-area product; it is not an inundated-pixel measurement.

## Decision

Classify the layer as **official event-impact context**. Do not use it as independent SAR validation, acquisition-time flood truth, or evidence that flooding caused the RTC-S1 backscatter response. Its multi-source composition, Sentinel-based validation, broad event scope, and absent feature-level dates prevent that inference.

The source is not added to the T163 hypothesis evidence set because it does not distinguish the competing explanations. The SAR pair remains diagnostic, and the existing physical-cause assessment remains unresolved. The bounded query, clipped geometry, source-response checksum, exact area calculation, and limitations are retained in [`rio-grande-do-sul-t163-official-impact-context-screen-2026-11-08.json`](../../data/research/rio-grande-do-sul-t163-official-impact-context-screen-2026-11-08.json).

## References

- [IEDE-RS affected-area service](https://iede.rs.gov.br/server/rest/services/ATLAS_DESASTRE_NATURAIS/area_diretamente_atingida_2024/MapServer)
- [CEMADEN Technical Note 469/2024](https://www.gov.br/cemaden/pt-br/assuntos/monitoramento/notas-tecnicas/nota-tecnica-no-469-2024-sei-cemaden-mapeamento-das-manchas-de-inundacoes-e-enxurradas-do-desastre-ocorrido-no-rio-grande-do-sul-em-abril-maio-2024/)
