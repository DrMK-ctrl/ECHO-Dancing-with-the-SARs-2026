# ANA Guaíba chronology in the T163 investigation

**Date:** 2026-11-08  
**Disposition:** Context linked; primary station series not retrieved; SAR interpretation unchanged.

## Source and scope

ANA's 2025 water-resources summary reports that the Usina do Gasômetro gauge (station `87444000`) remained above flood stage for 30 days, from 2024-05-02 through 2024-06-01. The date interval covers both Sentinel-1 acquisitions in the T163 case. This is an official agency narrative summary, not timestamped station observations. It does not measure water within the SAR AOI, validate the SAR or optical classifications, or establish a cause for the radar response. The linked H2 relationship is therefore `DOES_NOT_DISTINGUISH`; H2 remains `UNRESOLVED`.

The ANA legacy telemetry page identifies its former service as a secondary database and provides a service transition notice. Four bounded requests were retained for station `87444000` (raw and consistent modes), plus nearby station `87450020` in the same modes; each returned the service's no-data response. This does not establish that no historical archive exists. The public SGB HidroSeries page loaded, but its Shiny WebSocket remained in `CONNECTING` in this environment, so no series was retrieved. The primary gauge time series remains an open data-access item.

Sources: [ANA 2025 water and climate summary](https://conjuntura2025.ana.gov.br/agua-e-clima.html); [ANA legacy telemetry service notice](https://www.ana.gov.br/telemetria1ws/Dados.aspx); [ANA station reconfiguration notice](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs).

## Implementation and reproducibility

The retained context record is `data/research/ana-guaiba-official-flood-stage-context-2026-11-08.json` (SHA-256 `9d33a50197c9fb496ccfa895a3b7928a14ccf688e989420ec22cbdbbbc7e212b`). The assessment builder accepts it through `--guaiba-context-record`, checks source and case identity, the fixed reported interval, coverage of both SAR acquisition dates, and narrative-only interpretation limits. It adds a separate `OFFICIAL_HYDROLOGIC_EVENT_CONTEXT` artifact and a nondiscriminating relation under the water-change hypothesis.

The web endpoint repeats the case, source, interval, evidence-link, and relationship checks. The investigation panel labels the source as narrative context and offers a source-record inspector; the chronology is not placed on the exact-acquisition timeline. The updated T163 assessment is `data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-08.json` (SHA-256 `0d28407cd806e095ac3b1d120bdb23ead1e219ba4a2fde006e2a7ddd8f3b3582`). Its overall causal interpretation remains unresolved, and the Sentinel-1 RTC-S1 pair remains diagnostic.

## Verification

- Full suite: **273 passed**.
- Python compilation: `.venv/bin/python -m compileall -q echo tools/research/build_cross_sensor_investigation.py` passed.
- `git diff --check` passed.
- Firefox end-to-end check against the local application showed the ANA context card, narrative-only limits, linked source inspector, and H2 `UNRESOLVED / DOES_NOT_DISTINGUISH` relationship.
- Builder and web validation reject a reported period that fails to cover the SAR acquisitions, a claim that timestamped readings were retrieved, or an altered evidentiary relationship.

This work advances the evidence-assessment workflow without converting event chronology into a scientific measurement or resolving the underlying SAR cause.
