# First case review — Mozambique flood and NISAR GCOV

**Reviewed:** 2026-11-07

**Purpose:** Choose an evidence-backed first data case and record what is currently verifiable.

## Challenge and mission fit

The supplied ECHO mission directive defines the target as an interactive application using NISAR radar observations to visualize and investigate Earth-surface change. Its central science constraint is that a change in radar response is an observation, not a physical explanation. The official 2026 challenge detail page timed out or returned a gateway error during this review; the supplied challenge directive is therefore the working challenge brief until the official page can be independently rechecked.

NASA's 2026 event portal lists project submission opening on November 14 at 9:00 a.m. and closing November 15 at 11:59 p.m. local time. The project repository and implementation work before those dates are pre-event work and must be described as such in any submission. Current 2026 rules about pre-event code use, licensing, and local eligibility remain to be verified from the participant guides and Beirut event lead.

## Candidate case: southern Mozambique, January 2026

NASA's Scientific Visualization Studio describes NISAR observations of flooding along the Incomati and Limpopo rivers on January 17, 2026, with a comparison acquisition from January 5. It identifies the used data as observed NISAR GCOV, and describes the visualization as HH, HV, and an HH/HV ratio false-color composite. This establishes that the candidate is based on genuine NISAR acquisitions; it does not provide ECHO with raw data or independent ground truth.

### Live ASF catalog check

A live ASF `asf_search` metadata query was run for `dataset=NISAR`, `processingLevel=GCOV`, `dataMaturity=BETA`, point `33.5 E, 24.5 S`, dates January 1–31, 2026. It returned exactly two intersecting products:

| Observation | Start time UTC | Product | Collection / maturity |
| --- | --- | --- | --- |
| Before | 2026-01-05 03:42:32 | `NISAR_L2_PR_GCOV_009_114_A_165_4005_DHDH_A_20260105T034232_20260105T034253_X05010_N_P_J_001` | `NISAR_L2_GCOV_BETA_V1` / BETA |
| After | 2026-01-17 03:42:32 | `NISAR_L2_PR_GCOV_010_114_A_165_4005_DHDH_A_20260117T034232_20260117T034254_X05010_N_P_J_001` | `NISAR_L2_GCOV_BETA_V1` / BETA |

Both catalog entries match on relative path 114, frame 165, ascending direction, HH/HV main-band polarization, 40+5 MHz bandwidth, production configuration PR, and CRID X05010. Both cover the query point and are marked partial frame coverage. Their catalog HDF5 sizes are approximately 4.03 GB and 4.18 GB. ASF metadata footprints intersect, but actual valid-pixel overlap and grid registration have not been checked.

The pair is internally consistent at catalog level. Its January dates place it in the BETA collection; it must not be described as PROVISIONAL or fully calibrated. NASA describes GCOV diagonal measurements as terrain-corrected backscatter power in gamma-nought, with per-pixel QA masks and number-of-looks layers. Those layers and product QA reports must be reviewed before analysis.

## Evidence that must remain separate

- NASA's NISAR flood visualization is a useful published interpretation of the same NISAR observations. Because it uses those observations, agreement with it is not independent validation.
- NASA Earth Observatory's separate MODIS view documents the regional flood context but is optical and cloud-sensitive; it is not a pixel-level validation mask for NISAR.
- UNOSAT published a preliminary Sentinel-1 flood map dated January 5 for Sofala Province and explicitly says it was not field-validated. Its footprint has not yet been compared with the Chókwè AOI, so no agreement claim is available.
- A change in HH/HV gamma-nought is not by itself a flood classification or damage estimate. Any later water-extent result needs a defensible rule, QA exclusions, sensitivity tests, and suitable independent reference coverage.

## Access and current blocker

Catalog metadata is publicly searchable without downloading pixels. Earthdata Login is required to access product data. A local `.netrc` entry with mode `600` is now configured. A 1,024-byte HTTP range request returned `206 Partial Content` and reported the expected 4,034,920,448-byte January 5 HDF5 file size. Authenticated range-based HDF5 access was then used to read only `/science/LSAR/identification` from both products. No backscatter, mask, or other raster arrays were read, and neither full product was downloaded.

The two QA reports and their summary CSVs are stored locally under the ignored `data/products/` directory. Their hashes and extracted checks are recorded in [`data/cases/mozambique-2026/qa-review.json`](../../data/cases/mozambique-2026/qa-review.json); original QA files are not committed.

Both QA summaries report FAIL for “Passes all `identification` group checks?” They report PASS for opening the input, coordinate-grid metadata, calibration LUT metadata (crosstalk LUTs were skipped), decimated backscatter checks, and QA completion without exceptions. The QA report metadata shows `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`. The NISAR QA validator revision last changed before the report date expects `L-SAR` or `S-SAR` and a formatted observation-mode string. These are documented mismatches with that validator. The CSV does not enumerate individual failed checks, and the exact QA binary-to-source revision mapping remains unverified. The case is on **QA_HOLD** pending provider and version reconciliation.

Both products are cataloged as BETA. A passing calibration-LUT metadata check does not establish that BETA observations are fully calibrated. The QA summary's backscatter checks use decimated samples across the product, not the intended study area. Do not treat the pair as a scientific change result.

## Research sources

- NASA NISAR flood visualization, source data and interpretation: <https://svs.gsfc.nasa.gov/5661>
- ASF NISAR product discovery, maturity filtering, and Earthdata access: <https://nisar-docs.asf.alaska.edu/asf-search/>
- ASF NISAR product definitions and maturity: <https://nisar-docs.asf.alaska.edu/products-overview/>
- ASF GCOV measurement layers, RTC and QA fields: <https://nisar-docs.asf.alaska.edu/gcov/>
- ASF GCOV amplitude interpretation: <https://nisar-docs.asf.alaska.edu/amplitude/>
- NASA NISAR provisional GCOV collection description and limitations: <https://data.nasa.gov/dataset/nisar-provisional-geocoded-polarimetric-covariance-product-version-1-d9e04>
- NASA Earth Observatory flood context and MODIS imagery: <https://science.nasa.gov/earth/earth-observatory/floods-inundate-southern-mozambique/>
- UNOSAT preliminary Sentinel-1 flood product, Sofala Province: <https://unosat.org/products/4229>
- Official 2026 Space Apps event dates and local-time submission window: <https://www.spaceappschallenge.org/2026/>

## Current conclusion

The January pair is a verified, same-collection, same-acquisition-configuration metadata candidate and a practical pilot for the data-ingestion path. Authenticated access is operational. Both official QA summaries fail the identification-group check, and the products are BETA. No raster values or scientific result have been produced. Resolve the QA hold and select an analysis maturity appropriate to the science question before inspecting masks, common valid-pixel overlap, grid alignment, or change quantities.

## Additional source references

- NISAR GCOV data layers, masks, and backscatter values: <https://nisar-docs.asf.alaska.edu/gcov/>
- ASF NISAR data maturity, Earthdata Login, and streaming: <https://nisar-docs.asf.alaska.edu/asf-search/>
- ASF NISAR cookbook for authenticated streaming and AOI subsetting: <https://asfopensarlab.github.io/NISAR_Cookbook/search-stream-nisar-asf-search/>
- NISAR QA validator snapshot retrieved for this review: <https://github.com/isce-framework/nisarqa/blob/e43fc489ea1da7032f4c6da3c4dcf34a89bf8f0e/src/nisarqa/validate/sanity_checks.py>
