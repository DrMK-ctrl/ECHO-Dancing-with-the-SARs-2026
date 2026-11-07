# NISAR VALIDATED GCOV availability and case coverage

**Catalog checked:** 2026-11-07 03:22 UTC

**QA summary retrieved:** 2026-11-07 03:39–03:40 UTC

**Purpose:** Recheck whether the November VALIDATED release can replace the current QA-held candidates and verify the live catalog behavior.

## Findings

ASF's NISAR guide now identifies VALIDATED products as released in November 2026. It states they are fully calibrated and validated, and records incomplete L0B products as resolved with CRID `P05036`. The collection name returned for these products is `NISAR_L2_GCOV_V1`.

Using the repository-pinned `asf_search==14.1.0` client with `processingLevel=GCOV` and `dataMaturity=VALIDATED`:

| Query | Results | Interpretation |
|---|---:|---|
| Global, 2026-06-17 through 2026-11-07 | 197 | Returned products are in `NISAR_L2_GCOV_V1`, CRID `P05036`, with acquisition dates 2026-10-21 through 2026-10-23. |
| Nepal point, 2026-08-01 through 2026-09-30 | 0 | No VALIDATED GCOV candidate for the Rasuwa case period. |
| Mozambique point, 2026-01-01 through 2026-02-01 | 0 | No VALIDATED GCOV candidate for the pilot period. |
| Global, 2026-10-21 through 2026-10-24 | 210 | Products include same-orbit, same-frame granules whose acquisition times are seconds apart. The orbit-aware pair matcher returned zero temporal pairs. |

An authenticated metadata-only inspection of one real `P05036` VALIDATED product completed through the bounded HDF5 reader. The ASF catalog record also exposed its QA report and summary artifact URLs. The read requested 30,416,924 bytes of HTTP ranges because HDF5 metadata access has read amplification. It did not read radar measurement arrays or download the full product. This is access evidence, not a QA review or scientific measurement.

The latest catalog counts can change as indexing proceeds. ASF Search and CMR may also reflect updates at different times; catalog totals should be tied to the provider, query, and retrieval timestamp rather than treated as permanent archive counts.

## Per-product QA summary probe

The bounded QA-summary reader fetched the CSV for `NISAR_L2_PR_GCOV_033_141_D_085_4005_DHDH_A_20261021T235335_20261021T235345_P05036_N_P_J_001` from its canonical ASF product path. The 1,441-byte artifact has SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`. The request used Earthdata Login via local netrc and transferred one 1,441-byte HTTP range; no radar arrays were read.

The CSV reports **FAIL** for “Passes all identification group checks?”; it reports PASS for input opening, coordinate-grid metadata, calibration-LUT metadata, four decimated backscatter checks, and QA completion without exceptions. Its notes say crosstalk LUT checks were skipped and that backscatter checks used a decimated raster. The CSV does not state the QA software version.

ECHO's parser therefore returns a per-product `FAIL` disposition, retains every check row and note, and records the downloaded artifact's URI, retrieval time, and checksum. The NASA/ASF collection is labeled VALIDATED, while this product-level QA summary contains a failure. ECHO preserves both facts and does not treat collection maturity as a substitute for resolving the explicit check failure. This does not establish that the radar measurements are unusable or identify why the check failed; those interpretations remain open pending provider or validator evidence.

## Consequences for ECHO

- Support the exact `NISAR_L2_GCOV_V1` collection as VALIDATED, while retaining its actual CRID and product version in provenance. Do not infer maturity from an arbitrary collection-name token.
- Keep the Mozambique BETA and Nepal PROVISIONAL pair holds. VALIDATED GCOV is now present globally, but the current queried case periods have no matching products in that maturity.
- Keep the sampled VALIDATED scene out of measurement processing until the identification-check failure is understood or explicitly dispositioned.
- A temporal candidate must have different known NISAR orbit numbers and nonoverlapping acquisition intervals. Neighboring granules from one pass are spatial pieces of an acquisition, not before/after observations.
- Metadata candidate status remains weaker than QA review, pixel-grid registration, valid-pixel coverage, and scientific interpretation.

## Reproduction

Use `echo.catalog.CatalogQuery(..., maturity="VALIDATED")` or the `echo catalog --maturity VALIDATED` CLI option with the recorded region and dates. Search remains ASF metadata-only. A returned pair is a candidate only; the bounded reader and analysis gates remain separate.

## Sources

- ASF, [NISAR Data Products and maturity levels](https://nisar-docs.asf.alaska.edu/products-overview/).
- ASF, [NISAR VALIDATED known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- NASA CMR, [ASF collection directory](https://cmr.earthdata.nasa.gov/search/site/collections/directory/ASF/gov.nasa.eosdis).
- ASF, [ASF Search API keywords](https://docs.asf.alaska.edu/api/keywords/).
