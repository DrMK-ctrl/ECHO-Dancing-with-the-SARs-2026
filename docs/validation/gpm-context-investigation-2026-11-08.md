# GPM context in the Rio Grande do Sul investigation

**Case:** `rio-grande-do-sul-t163-349925-diagnostic-2024`
**Status:** NASA precipitation context retrieved; alternative surface-driver explanation remains unresolved and untested

## Retrieval

ECHO authenticated with the configured local Earthdata `.netrc` and retrieved NASA GPM IMERG Final Daily V07 (`GPM_3IMERGDF`, DOI `10.5067/GPM/IMERGDF/DAY/07`) through the NASA Harmony OGC API EDR cube. Fourteen requests returned bounded NetCDF4 subsets for a 0.6° × 0.5° regional neighborhood: 1–7 May 2024 and 25–31 May 2024. Each window ends before its corresponding OPERA RTC-S1 acquisition (8 May and 1 June). No global IMERG files were downloaded.

The returned 0.1° grid contains six longitude and five latitude centers. The AOI is only about 0.01° wide; the assessment uses the nearest native cell centered near 51.25°W, 30.05°S and retains the surrounding regional values without resampling. The product's `precipitation` field is a daily mean rate estimate in mm/day. The `precipitation_cnt` field records valid half-hourly retrievals. All 14 nearest-cell days report 48 of 48 nominal samples.

## Observed context

| Pre-acquisition window | Seven daily estimates at nearest cell | Sum of daily estimates | Sampling |
| --- | --- | ---: | --- |
| 1–7 May | 71.39, 110.34, 3.58, 12.44, 21.33, 0.35, 0.43 mm/day | 219.87 mm | 7/7 days at 48/48 |
| 25–31 May | 0.00, 0.09, 14.25, 0.00, 0.00, 0.00, 0.00 mm/day | 14.33 mm | 7/7 days at 48/48 |

This establishes materially different regional precipitation context before the two observations. It does not establish rainfall at the AOI scale, soil moisture, flood extent, a causal relationship to the SAR response, or provider QA acceptance of RTC-S1.

## Investigation effect

The two GPM records are attached to H3, “other land-surface or acquisition effects,” with the explicit relationship `DOES_NOT_DISTINGUISH`. H3 remains `UNRESOLVED` and `NOT_TESTED`: precipitation is related context, not a direct measurement of soil moisture or the SAR-scale surface state. F5 now records GPM as retrieved with quality limits; F6 identifies the next evidence need—screen for independent soil-moisture, vegetation, or in-situ observations with useful spatial support and timing. H2 (water change explains SAR response), the overall causal disposition, and the RTC-S1 QA hold remain unresolved.

## Reproducibility and verification

- Retrieval implementation: `tools/research/retrieve_gpm_daily_context.py`.
- Source records: `data/research/gpm-imerg-context-T163-349925-before-2024-05-08.json` and `data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json`.
- The records identify NASA GES DISC, mission, product/version, DOI, Harmony collection and endpoint, daily granule IDs, native grid coordinates, variables, dates, retrieval time, bytes, and SHA-256 for every bounded subset.
- The assessment builder checks the two date windows against SAR acquisition dates and verifies each returned-subset checksum. The application repeats those checks when loading the assessment.
- Focused Firefox walkthrough: opened the optical-context view, opened the investigation, inspected the GPM source record, and confirmed that the non-causal boundary and next-observation gap appear in the interface.
- Full software test suite: 245 passed. Python bytecode compilation passed. Node.js is not installed, so standalone Node syntax checking was unavailable; the updated JavaScript executed in headless Firefox.

## References

- [NASA GES DISC GPM_3IMERGDF V07 dataset](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary)
- [NASA IMERG V07 technical documentation](https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation)
- [NASA Harmony API documentation](https://harmony.earthdata.nasa.gov/docs)
