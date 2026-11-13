# NASA NISAR-format sample GCOV pair screen

**Screened:** 2026-11-13 03:59 UTC  
**Disposition:** rejected for accepted temporal analysis; both provider summaries report `FAIL`.

## Why this pair was checked

NASA's sample-data suite links two L2 GCOV acquisitions over the same sample area. NASA's data overview explicitly identifies the sample suite as products made from JAXA ALOS-1 PALSAR data to serve as NISAR-format surrogates. These are useful for developing software compatibility, but they are not measurements acquired by NISAR in orbit. The exact products span 46 days:

| Acquisition start (UTC) | Product |
|---|---|
| 2008-10-12 06:09:11 | `NISAR_L2_PR_GCOV_001_030_A_019_2800_SHNA_A_20081012T060911_20081012T060925_D00404_N_F_J_001` |
| 2008-11-27 06:10:00 | `NISAR_L2_PR_GCOV_002_030_A_019_2800_SHNA_A_20081127T061000_20081127T061014_D00404_N_F_J_001` |

NASA reports that the surrogate format and metadata were designed to be compatible with planned NISAR products. That compatibility does not change the mission or instrument that acquired the source data.

## Bounded source checks

For each HDF5 product, an HTTP byte-range probe requested byte `0` only. Both returned `206`, with a reported total object size of 171,966,464 bytes. No HDF5 metadata or measurement arrays were read, and neither product was downloaded.

Each canonical sample QA summary is 500 bytes. The exact CSV was retrieved and retained under [`data/research/nasa-gcov-sample-pair-qa-2026-11-13/`](../../data/research/nasa-gcov-sample-pair-qa-2026-11-13/), with source URI, retrieval details, check rows, and SHA-256 values in [`screen.json`](../../data/research/nasa-gcov-sample-pair-qa-2026-11-13/screen.json). Both artifacts have SHA-256 `18176a216d79fe32f08ca3b4e5d193241f7f0cb00172657701dccd1e963621a7`.

Both summaries contain five check rows. `Passes all identification group checks?` is `FAIL`; the other four listed rows are `PASS`. This is the provider's reported disposition. ECHO did not infer which identification field caused the aggregate failure or replace the provider result. The sample summaries also do not contain the full set of check names required by ECHO's current production-GCOV QA contract.

## Decision

Do not use this pair to produce an accepted temporal change result. Its NASA-provided NISAR-compatible format makes it a possible software-development surrogate, while the ALOS-1 origin and provider QA failures make it unsuitable as a validated in-orbit NISAR finding or as an accepted analysis input under the current gates. No product metadata, grids, masks, or measurement values were read; no comparison or physical interpretation was produced.

This check does not resolve the QA holds on the actual Iraq NISAR products and does not establish that every NASA sample product has the same QA outcome.

## Sources

- NASA, [NISAR Sample Data](https://science.nasa.gov/mission/nisar/sample-data/), which lists both GCOV dates and product links.
- NASA, [NISAR Data Overview](https://science.nasa.gov/mission/nisar/data/), which identifies the sample products as ALOS-1 PALSAR-derived surrogates.
- ASF DAAC source artifacts and exact product URLs are preserved in the linked machine-readable screen record.
