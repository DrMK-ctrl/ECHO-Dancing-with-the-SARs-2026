# NISAR VALIDATED GCOV coverage refresh — 2026-11-08

## Finding

A bounded extension of the global ASF catalog screen found no VALIDATED GCOV scenes from 2026-09-20 through 2026-10-20. The prior complete screen for 2026-10-21 through 2026-11-07 contains 993 unique scenes and one metadata-compatible temporal pair, with no daily result window reaching its configured cap. A query for 2026-11-08 at 11:46 UTC returned no scene; that calendar day was still in progress.

The sole catalog pair remains:

- Before: `NISAR_L2_PR_GCOV_034_011_A_017_4005_DHDH_A_20261024T224955_20261024T225027_P05036_N_F_J_001`
- After: `NISAR_L2_PR_GCOV_035_011_A_017_4005_DHDH_A_20261105T224956_20261105T225027_P05036_N_F_J_001`
- Interval: 12 days; metadata reports intersecting footprints and matching path, frame, direction, coverage, polarization, bandwidth, production configuration, and CRID.
- Disposition: `QA_HELD`. Both ASF summaries report aggregate identification-group `FAIL`; the QA review records `LSAR` and `(NOT SPECIFIED)` observation-mode metadata. No measurement arrays were read and no temporal measurement was created.

## Search coverage and provenance

The earlier VALIDATED screen used one-day date windows through ASF's paginated `asf_search.search_generator`, deduplicated by scene ID, with a per-day maximum of 2,000 results. There were no capped windows. The new earlier window used the same procedure for 31 days. The November 8 query covered the available catalog state at 11:46 UTC only.

Exact records, UTC retrieval times, result counts, pair identity, and SHA-256 references are consolidated in [`validated-gcov-coverage-refresh-2026-11-08.json`](../../data/research/validated-gcov-coverage-refresh-2026-11-08.json). Raw screen records are retained alongside it. The QA review is [`validated-gcov-temporal-pair-qa-review-2026-11-07.json`](../../data/research/validated-gcov-temporal-pair-qa-review-2026-11-07.json).

## Decision for the next search

The September 20–October 20 interval is closed for this VALIDATED-GCOV screen; repeating it without an archive update would add no evidence. Do not retry the held October 24/November 5 pair as a new candidate unless ASF changes a product, QA report, or documented validation rule. Continue checking newly completed acquisition dates as catalog coverage matures, and advance independent investigation work with accurately labeled diagnostic observations. The search does not show that no suitable product exists outside the screened dates or other mission/product collections.

This is a catalog-coverage result, not a temporal SAR analysis, product-QA clearance, change measurement, or event finding.
