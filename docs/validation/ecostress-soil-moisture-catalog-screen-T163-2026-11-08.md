# ECOSTRESS soil-moisture catalog screen — T163

**Date:** 2026-11-08

**Result:** No granule coverage for either target interval; no measurement retrieved.

## Question

Does NASA LP DAAC's ECOSTRESS `ECO_L3G_SM` Version 2 collection contain a candidate near both T163 diagnostic SAR acquisitions (2024-05-08/09 and 2024-06-01/02) for the bounded Rio Grande do Sul AOI (`[-51.24, -30.04, -51.23, -30.03]`)?

## Method and result

Queried NASA CMR's granule search endpoint using the exact short name and version. Searches covered each acquisition-centered window over both the AOI and a regional bounding box. Each returned HTTP 200 with zero hits. A global April 1 through July 1, 2024 query also returned zero hits; the global March 2024 positive control returned 377 hits, confirming the collection and endpoint were searchable.

The query intervals, CMR hit counts, product identity, and interpretation limits are retained in [`ecostress-soil-moisture-catalog-screen-T163-2026-11-08.json`](../../data/research/ecostress-soil-moisture-catalog-screen-T163-2026-11-08.json).

NASA's dataset record describes a linear-regression estimate using GEOS-5 FP soil moisture and ECOSTRESS surface-temperature, NDVI, and albedo predictors, followed by GEOS-5 bias correction. NASA JPL summarizes the V2 layer as GEOS-5 reanalysis soil moisture resampled to ECOSTRESS resolution. The 70 m grid therefore does not represent direct 70 m soil-moisture measurements. See the [NASA dataset record](https://data.nasa.gov/dataset/ecostress-gridded-downscaled-soil-moisture-instantaneous-l3-global-70-m-v002-96acf) and [ECOSTRESS product algorithm summary](https://ecostress.jpl.nasa.gov/data/atbds-summary-table).

## Disposition

This product cannot test T163's soil-moisture branch at the target dates because CMR lists no granules worldwide in the broader interval. No data were downloaded, no pixel quality was evaluated, and no scientific conclusion or hypothesis disposition changed. This closes only the ECOSTRESS product/date route; the independent surface-state evidence search remains open.
