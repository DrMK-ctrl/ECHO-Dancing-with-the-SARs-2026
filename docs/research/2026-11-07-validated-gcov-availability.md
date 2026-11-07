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

## Live recheck and bounded QA sample

A follow-up global ASF search on 2026-11-07 at 05:10 UTC, for VALIDATED GCOV from 2026-10-21 through 2026-11-07 (maximum 250 results), returned at least 250 features; the API result was capped, so this is not a collection count. Three fresh point searches around Istanbul (28.990° E, 41.105° N), Rasuwa (85.55° E, 28.30° N), and southern Mozambique (33.5° E, 24.5° S), each covering 2026-07-01 through 2026-11-07, returned zero VALIDATED features. Thus the newer global release did not provide an observed replacement for those candidate areas in these queries.

Four features from the bounded global result were sampled in returned order, taking the first feature for each of four distinct ASF path numbers (4, 26, 156, and 158). Their exact scene IDs, catalog metadata, QA CSV and PDF URIs, retrieval times, checks, and checksums are preserved in [`validated-qa-sample-2026-11-07.json`](../../data/research/validated-qa-sample-2026-11-07.json). All four are P05036 products with acquisition dates 2026-10-23 through 2026-10-26. Each QA summary reports exactly one failed check, “Passes all `identification` group checks?”; every other listed check passes, including the decimated backscatter checks. Each corresponding QA report identifies software 17.2.0, product specification 1.6.0, and product version 1.0.20. All report `instrumentName=LSAR` and `listOfObservationModes=["(NOT SPECIFIED)"]`; ECHO's limited source-code cross-check marks the same two fields as matching known v17.2.0 failure rules, and each report's orbit, track, and frame match its catalog record.

This small, query-order-dependent sample is not a global QA census, and the QA CSV does not identify its software version or enumerate the failed subchecks. The four retained CSV hashes differ; separate earlier candidate scenes had repeated CSV bytes, so hashes are preserved and never counted as independent diagnostics by themselves. The repeated identification-group failure supports keeping the per-product QA gate closed; it does not establish that radar measurements are invalid, nor does it establish that the two observed fields are the only cause. The currently linked public GCOV specification, Rev F version 1.5.0, describes these fields but does not enumerate their allowed values; its relationship to the sampled products' reported specification version 1.6.0 is unresolved. The check therefore cannot be independently waived from the public specification alone.

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

## Global temporal-window recheck

At 2026-11-07 13:41 UTC, ECHO repeated this global scan with `asf_search.search_generator` pagination, a 2,000-result daily ceiling, and stable scene-ID deduplication. The 18 daily windows returned 993 unique scene IDs with no capped window and 13 observed acquisition dates through November 5. October 22 alone returned 500 records over two pages; the earlier 250-record result was incomplete. Counts also changed between the two paginated scans, showing that ASF indexing was still updating during this review.

The expanded catalog produced one orbit-aware metadata pair: October 24 to November 5, 2026, 12 days apart, both VALIDATED `NISAR_L2_GCOV_V1` / CRID `P05036`, ascending path 11, frame 17, full frame coverage, and HH/HV polarizations. This is a metadata match only. ASF QA summaries for both exact products report **FAIL** on “Passes all identification group checks?”; the other eight listed summary checks pass. Their QA reports both record `instrumentName=LSAR` and `listOfObservationModes=["(NOT SPECIFIED)"]`. A partial comparison with `nisarqa` v17.2.0 finds those values conflict with its instrument-name and observation-mode rules. That source-code check is diagnostic and does not replace or override the provider's aggregate FAIL. ECHO therefore held the pair before reading product metadata arrays or radar measurement arrays; no temporal measurement exists.

This resolves the earlier catalog-pagination uncertainty, but not the provider QA hold. The exact QA evidence and its limits are preserved in [`validated-gcov-temporal-pair-qa-review-2026-11-07.json`](../../data/research/validated-gcov-temporal-pair-qa-review-2026-11-07.json) and summarized in [the pair review note](2026-11-07-validated-gcov-pair-screen-review.md).

The machine-readable output, including page counts per date window, compact matching metadata, geometries, a checksum of each complete provider feature, truncation flags, acquisition dates, and the exact pair-matcher output, is preserved in [`validated-gcov-global-time-series-2026-11-07.json`](../../data/research/validated-gcov-global-time-series-2026-11-07.json). Reproduce or refresh it with:

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py
```

The temporal screen is metadata-only. It does not establish pixel support for a selected AOI, per-product suitability, valid-pixel overlap, or physical change. The QA-held pair was not sent to the pair pixel reader.

## Earlier bounded global coverage check

To avoid repeating previously empty dates, ECHO also screened VALIDATED GCOV globally with the repository-pinned daily, paginated ASF query for three additional nonoverlapping ranges:

| Acquisition dates queried | Unique scenes | Metadata pairs | Retained catalog record |
|---|---:|---:|---|
| 2026-08-01 through 2026-08-31 | 0 | 0 | [`August screen`](../../data/research/validated-gcov-global-time-series-2026-08.json) |
| 2026-09-01 through 2026-09-30 | 0 | 0 | [`September screen`](../../data/research/validated-gcov-global-time-series-2026-09.json) |
| 2026-10-01 through 2026-10-20 | 0 | 0 | [`October 1–20 screen`](../../data/research/validated-gcov-global-time-series-2026-10-01-20.json) |

The adjacent October 21–November 7 global screen returned 993 unique catalog scenes and one metadata pair (October 24–November 5, 12 days apart). Both exact pair products' provider QA summaries report the identification-group check as FAIL, so the pair remains held before product arrays are read. These screens bound observed catalog availability for the stated periods; they do not prove the archive is complete or that earlier acquisitions cannot be processed or released later. Future searches should advance the end date as new acquisitions or reprocessing become available rather than replay these empty windows without a new catalog or processing signal.

## Reproduction

Use `echo.catalog.CatalogQuery(..., maturity="VALIDATED")` or the `echo catalog --maturity VALIDATED` CLI option with the recorded region and dates. Search remains ASF metadata-only. A returned pair is a candidate only; the bounded reader and analysis gates remain separate.

## Sources

- ASF, [NISAR Data Products and maturity levels](https://nisar-docs.asf.alaska.edu/products-overview/).
- ASF, [NISAR VALIDATED known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- ISCE Framework, [GCOV QA and attribute issue #216](https://github.com/isce-framework/isce3/issues/216) and [`nisarqa` placeholder-validation pull request #155](https://github.com/isce-framework/nisarqa/pull/155), checked 2026-11-07. These provide validator-rule context; they do not replace the exact product's QA artifacts or independently disposition its failure.
- NASA CMR, [ASF collection directory](https://cmr.earthdata.nasa.gov/search/site/collections/directory/ASF/gov.nasa.eosdis).
- ASF, [ASF Search API keywords](https://docs.asf.alaska.edu/api/keywords/).
