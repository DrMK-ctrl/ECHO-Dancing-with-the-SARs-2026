# Guaíba gauge context screen — T163-349925 — 2026-11-08

## Result

ANA/SGB's Usina do Gasômetro emergency gauge is about 669 m from the center of the T163 AOI and operated across both Sentinel-1 acquisition dates. It is a promising source for nearby hydrologic context, but it measures river level at one point; it cannot establish water extent within the SAR pixels or validate a SAR-derived flood boundary.

A contemporary published chart reproducing ANA/SEMA daily minima reports 5.00 m on 8 May and 3.51 m on 1 June 2024. These are secondary values and are not exact-time readings at the SAR acquisitions. ECHO therefore did not add them to the case evidence or use them to explain the backscatter change.

## Access and provenance findings

- The official SGB station map identifies the current Usina do Gasômetro gauge at `(-51.24194, -30.03472)`. The T163 AOI center is `(-51.235, -30.035)`.
- The public SACE CSV was retrieved and checksum recorded, but its 2,968 observations span only 2026-10-07 through 2026-11-07; it does not cover the 2024 acquisitions.
- One request to ANA's legacy `HidroSerieHistorica` endpoint for station `87444000` and 2024-05-08 through 2024-06-02 returned HTTP 200 with an XML “no data for station in requested period” error. The endpoint's response does not establish that the historical observations are absent.
- ANA/SGB document that station `87444000` preserves the emergency readings from 2024-05-03 through 2025-08-29, while the corrected historical series is available as station `87450020` after a 1.18 m datum adjustment. The identifiers and vertical references must not be silently combined.
- ANA's current HidroWeb service documents an authenticated telemetric-series route. No credentials or access token were used or stored in this screen.

## Disposition

`PRIMARY_HISTORICAL_SERIES_NOT_RETRIEVED`. The gauge is a viable follow-up for temporal water-level context if ECHO obtains the primary, timestamped series with quality fields. Even if retrieved, it would remain contextual support: a river gauge cannot validate the local SAR water mask or independently establish why backscatter changed.

The structured access record is [here](../../data/research/guaiba-gauge-context-screen-T163-349925-2026-11-08.json). It links the retained [SACE CSV export](../../data/research/source-artifacts/ana-sgb-guaiba-current-cota-2026-10-07_2026-11-07.csv) and [legacy endpoint response](../../data/research/source-artifacts/ana-guaiba-historical-query-no-data-2026-11-08.xml) by SHA-256.

## Sources

- ANA, [station change and datum adjustment](https://www.gov.br/ana/pt-br/assuntos/noticias-e-eventos/noticias/ana-e-servico-geologico-do-brasil-fazem-readequacoes-em-estacao-de-monitoramento-do-rio-guaiba-em-porto-alegre-rs).
- SGB, [Guaíba station map](https://sace.sgb.gov.br/niveis/estacoes_mapa.php?bacia=guaiba) and [public SACE level CSV](https://sace.sgb.gov.br/niveis/api/dados/guaiba_72_cota.csv).
- ANA, [HidroWeb service documentation](https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html).
- Jornal do Comércio, [2024-06-03 issue](https://digital.jornaldocomercio.com/jcomercio/2024/06/03/1537c7/issue11924.pdf), which attributes its daily minima chart to ANA and SEMA/RS; treated here as secondary reporting only.
