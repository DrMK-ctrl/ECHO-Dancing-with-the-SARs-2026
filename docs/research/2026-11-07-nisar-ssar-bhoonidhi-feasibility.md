# NISAR S-SAR GCOV through Bhoonidhi: feasibility review

**Reviewed:** 2026-11-07  
**Status:** Bounded catalog-search client implemented; no S-SAR product retrieved or validated

## Why this was examined

The ASF-distributed NISAR L-SAR GCOV products inspected by ECHO report a provider QA failure in the identification group. To find a scientifically legitimate alternative without relaxing that gate, this review checked whether authentic NISAR S-SAR GCOV data and its provider QA artifacts are available through ISRO's Bhoonidhi service.

## Findings from primary provider documentation

- NASA/ASF's NISAR availability guide says S-band sample RSLC, GSLC, and GCOV products from January and February 2026 are available through Bhoonidhi. ISRO's current release page documents routine S-SAR product generation from Cycle 25, which began 2026-07-08, with GCOV among the released products. The current release is identified as product baseline 1.4.0 / CRID P00500. These are authentic NISAR S-SAR mission products distributed by ISRO, not ASF/JPL L-SAR products.
- ISRO's product-format document describes the HDF5 S-SAR science root as `/science/SSAR`, with GCOV data below `/science/SSAR/GCOV`. It describes real-valued covariance layers as absolute gamma0 power and specifies a per-pixel `rtcGammaToSigmaFactor` for conversion to sigma0. The document says the S- and L-band structures share a common format with the corresponding science root changed by instrument, while also documenting ISRO-specific additions. This suggests reusable numerical primitives may apply, but does not establish implementation compatibility with ECHO's current reader or suitability of any particular pair.
- ISRO's NISAR QA-format document specifies separate QA artifacts, including a QA log, QA report, QA statistics HDF5, and QA summary CSV. It states that the CSV's `REASON` column is populated for product QA failures. Such a product-specific reason may resolve more than the aggregate identification-group result available in the currently inspected ASF CSV.
- ISRO reports the current S-band baseline has known residual radiometric banding in low-SNR homogeneous areas and residual RFI artifacts may remain. These limitations would need to be carried into scene selection and interpretation; they do not automatically disqualify all scenes.
- Bhoonidhi's API lists the `NISAR_SSAR_GCOV` collection and supports spatial/time search, but requires an authenticated bearer token. A direct unauthenticated collection request returned HTTP 401. No credentials or token were used or stored.

## ECHO integration boundary

ECHO currently searches and reads ASF-hosted NISAR L-SAR GCOV. It assumes the L-SAR HDF5 tree and ASF product URLs, and its current provider-QA parser recognizes ASF's CSV schema. The first separate S-SAR boundary now exists in `echo.bhoonidhi`: it requests only the `NISAR_SSAR_GCOV` STAC collection, filters to products with `Online=Y`, limits each query to at most 500 items, retains the raw provider FeatureCollection, and records the query, retrieval time, provider, instrument, and response checksum. The CLI prompts for account credentials without echoing the password; the access token remains in process memory and is not included in output. This is catalog discovery only. It does not download S-SAR products, parse ISRO QA artifacts, normalize items into ASF records, or clear any analysis gate.

Do not convert S-SAR data into an ASF-shaped record or mark it compatible based only on the shared GCOV concept. First retrieve an actual product and its provider QA artifacts, verify the format against this versioned ISRO specification, inspect scene-specific quality and calibration information, and establish a suitable repeated-acquisition pair. Only then determine whether the existing gamma0 comparison primitive can be reused behind an explicit compatibility gate.

## Next evidence needed

1. Run the bounded authenticated query for a location/time with repeated S-SAR GCOV acquisitions, including full STAC items and online status.
2. Conduct one small product access probe and retrieve its associated QA summary/log/report, recording source identifiers, retrieval time, product baseline, and checksums.
3. Verify versioned, scene-specific product identity, gamma0 layer semantics, mask handling, grid geometry, and provider QA outcome.
4. Review compatibility and resource use before connecting S-SAR to the application's measurement workflow.

The Bhoonidhi API requires a registered account and bearer token. The token is short-lived and must remain local; it must not be committed to ECHO or pasted into chat.

## References

- NASA/ASF, [Available NISAR Data](https://nisar-docs.asf.alaska.edu/availability-overview/).
- NASA/ASF, [Accessing NISAR Data](https://nisar-docs.asf.alaska.edu/access-overview/).
- ISRO/Bhoonidhi, [S-SAR data release and product documents](https://bhoonidhi.nrsc.gov.in/NISAR/NisarProducts.html), including baseline P00500, known residual banding/RFI limits, and current global daily product coverage.
- ISRO, [NISAR L & S Band Level-1 and Level-2 Data Product Format Document v1.2.1](https://bhoonidhi.nrsc.gov.in/NISAR/NISAR_Data_Product_Format_Document_V1.2.1_digisigned.pdf).
- ISRO, [NISAR L & S Band Level-1 and Level-2 QA Data Product Format Document v1.0](https://bhoonidhi.nrsc.gov.in/NISAR/NISAR_QA_Product%20Format%20Document_digisigned.pdf).
- ISRO/Bhoonidhi, [API specification](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/).
- NASA/ASF, [Vertex instrument availability](https://nisar-docs-test.asf.alaska.edu/vertex), which distinguishes ASF L-band holdings from ISRO Bhoonidhi S-band distribution.

## Bounded discovery implementation

The catalog client uses the documented Bhoonidhi `/auth/token` and `/data/search` endpoints. It prompts for credentials at runtime, requests one in-memory bearer token, and performs a single bounded POST for one WGS84 rectangle and acquisition-time interval. The returned raw FeatureCollection is retained in a JSON envelope with the exact query, UTC retrieval time, and SHA-256 of the response bytes. Pagination is recorded but not followed automatically. Credentials and token are excluded from the artifact. Regression tests cover request construction, metadata retention, validation, and authentication failures. Live authenticated behavior and the response schema for actual S-SAR GCOV items remain unverified until the query is run with a registered Bhoonidhi account.
