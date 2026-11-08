# Decision 0039: link ANA's Guaíba flood-stage chronology as narrative context

**Date:** 2026-11-08  
**Status:** Implemented for the T163 diagnostic investigation

## Decision

Link ANA's published statement that Usina do Gasômetro station `87444000` remained above flood stage for 30 days from 2024-05-02 through 2024-06-01 to the T163 investigation as `OFFICIAL_HYDROLOGIC_EVENT_CONTEXT`.

This is an agency narrative summary, not the timestamped primary gauge series. The reported period overlaps both Sentinel-1 acquisitions and provides regional event chronology. It is not an AOI water measurement, does not validate the optical product classes or SAR response, and cannot establish why backscatter changed. Its relationship to the water-change hypothesis is therefore `DOES_NOT_DISTINGUISH`; the hypothesis remains unresolved and the RTC-S1 pair remains diagnostic.

## Implementation

- The retained context record identifies the provider, source page, station code, reported date range, and retrieval time, and explicitly states that no timestamped readings were retrieved.
- The assessment builder checks source identity, case identity, the reported interval, and coverage of both SAR acquisition dates. It rejects a record that claims to contain primary gauge readings or omits the AOI-scale interpretation limit.
- The linked assessment records the chronology as a distinct evidence artifact and cites it under the water hypothesis without changing its disposition.
- The map-centered investigation panel labels the entry as narrative context and opens the checksummed source record. It does not place a date-range narrative on the exact-acquisition timeline.
- The web layer rechecks the record identity, source URL, period linkage, narrative-only state, and nondiscriminating relationship before serving the assessment or linked artifact.

## Reproduction

Build the T163 assessment with `tools/research/build_cross_sensor_investigation.py` and the retained T163 SAR, DSWx-HLS, spatial-support, polarization, GPM, SMAP, and HLS records, adding:

```bash
--guaiba-context-record data/research/ana-guaiba-official-flood-stage-context-2026-11-08.json
```

The full command and interface verification are recorded in [the validation report](../validation/ana-guaiba-context-investigation-2026-11-08.md). The primary time series remains a separate open data-access task; this record does not satisfy it.

## Source

- ANA, [Conjuntura dos Recursos Hídricos no Brasil 2025 — water and climate](https://conjuntura2025.ana.gov.br/agua-e-clima.html).
- ANA, [station change and datum adjustment](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs).
