# Newer VALIDATED-GCOV repeat candidates — 2026-11-13

## Question and bounded catalog recheck

Did the next available global NISAR GCOV acquisitions add a repeat candidate after the retained October 9–November 8 VALIDATED catalog, and did any new exact product pair clear ASF's provider QA summary?

The existing `screen_validated_gcov_time_series.py` workflow queried the half-open interval `[2026-11-10, 2026-11-14)` for all three maturities, with a four-day query window, one-page responses, a 90-second CMR timeout, and no result-cap hits. The [VALIDATED catalog record](../../data/research/validated-gcov-global-time-series-2026-11-10-13.json), SHA-256 `c4b729c7875bc29277495493e9a18d6d1f7d84fd5e1a1c7eec34b10f4ae9845f`, contains 19 scenes, all acquired on November 10. The November 11–13 dates had no scenes in this completed catalog response. PROVISIONAL and BETA returned zero scenes for the same requested interval; their record hashes are `ec30ea423131f995ef3bb4757c3fbcb3ae0a995a06b85fac84a22f1c3d1f2175` and `4a73e1a45f64d641eba1d2b5a005c41895d84eefff370a2bc1e4efc7051102fc`, respectively. These are time-bounded catalog results, not statements about later catalog updates or the entire archive.

The November 10 VALIDATED scenes are P05036. Pairing them against the retained October 9–November 8 catalog yields 12 metadata-compatible cross-window repeats: seven full/full and five with at least one partial frame. The selected pair/input records preserve both parent catalog paths and checksums, the exact features, and the matching criteria. The parent catalogs are separate snapshots with a November 9 coverage gap; the derived inputs explicitly retain that limitation.

## Exact-product QA result

All 12 new pair candidates were screened using exact ASF QA-summary CSVs for their 24 products. The first full/full candidate (path 77/frame 78, October 29–November 10) is in its own screen record; the other 11 pairs are in a second record. All 24 retrievals succeeded. Every summary reports provider disposition **FAIL** on the aggregate identification group; every other check reported in each summary passes. The initial screen retrieved no QA report PDFs, HDF5 metadata, arrays, masks, or pixel measurements.

| Cohort | Pairs | Products | Provider FAIL | Retrieval errors | QA record SHA-256 |
|---|---:|---:|---:|---:|---|
| Path 77/frame 78, full/full | 1 | 2 | 2 | 0 | `597dc682c71438700c18e0288faed4509f02bd943354b1092f92b2837e7c8e43` |
| Other cross-window repeats | 11 | 22 | 22 | 0 | `4cecb0e387f9c4019de796eb7c1ef4b64e3acf5bb9724bda9cbbf58869784200` |

The complete product records retain retrieval timestamps, exact scene IDs, summary checks, and checksums: [path 77/frame 78 QA JSON](../../data/research/validated-gcov-p05036-path77-frame78-cross-window-qa-2026-11-13.json) and [other-pairs QA JSON](../../data/research/validated-gcov-p05036-path77-other-cross-window-pairs-qa-2026-11-13.json). Their inputs, selection records, and scene lists are linked below:

- Path 77/frame 78: [catalog input](../../data/research/validated-gcov-p05036-path77-frame78-cross-window-input-2026-11-13.json), [selection](../../data/research/validated-gcov-p05036-path77-frame78-cross-window-selection-2026-11-13.json), and [scene IDs](../../data/research/validated-gcov-p05036-path77-frame78-cross-window-scene-ids-2026-11-13.txt).
- Other repeats: [catalog input](../../data/research/validated-gcov-p05036-path77-other-cross-window-pairs-2026-11-13-input.json), [selection](../../data/research/validated-gcov-p05036-path77-other-cross-window-pairs-2026-11-13-selection.json), and [scene IDs](../../data/research/validated-gcov-p05036-path77-other-cross-window-pairs-2026-11-13-scene-ids.txt).

### Diagnostic report review of the full/full pair

After preserving its CSV dispositions, ECHO retrieved the canonical QA report PDFs for the two path 77/frame 78 products. Both reports parsed completely under the supported product contract. The pinned partial source cross-check against `nisarqa` 17.2.0 found the same rule mismatches in each report: `instrumentName=LSAR` and `listOfObservationModes=["(NOT SPECIFIED)"]`. This establishes those values are present in the PDF metadata and conflict with the cited validator rules; it does **not** establish that either field caused ASF's aggregate CSV failure. The PDF explicitly has `provider_qa_disposition=NOT_IN_REPORT_PDF`, so ASF's CSV `FAIL` remains controlling. The parsed metadata, validator reference, retrieval provenance, and PDF checksums are retained in the [report review record](../../data/research/validated-gcov-p05036-path77-frame78-cross-window-report-review-2026-11-13.json), SHA-256 `94a0dee5197669f7fed75d53bc8f10d315c825beadededca32bed490ad1e10f5`. PDF SHA-256 values are `b426fd4622539d074e5efd3ba6d8f8635ea7a3a0a889cd5a0f35ff970afc2659` (Oct 29) and `d3222be95534ea8ceb36978b12cd7797afad752d60e7a281b6f612ed25b26597` (Nov 10). No PDF was requested for the other 22 products.

The new 24 scene IDs were absent from all previously retained exact-product QA records before this screen. Combined with the previous bounded catalog screen, ECHO now has exact provider summary evidence for 132 distinct P05036 products: 108 products across the original 54 candidates and 24 products across these 12 new cross-window pairs. This is still bounded evidence; it does not establish that all P05036 products, all maturities, or the NISAR archive fail QA.

## Interpretation and next scientific gate

The new acquisitions do not resolve the temporal-comparison bottleneck. The aggregate identification-group failures do not identify which provider field failed. The two detailed reports show source-rule mismatches, but neither the reports nor the CSVs attribute ASF's aggregate failure to those fields. No pair may proceed to ECHO's measurement comparison while either exact product remains QA-held. Do not infer a surface-change result from these QA summaries.

The November 10 observations demonstrate that additional VALIDATED scenes are arriving, but the available November 10 cohort and its 12 repeat candidates do not provide a QA-cleared pair. Further repeats of unchanged P05036 QA summaries are not justified without a new product version, a provider correction, or another material source of evidence. ECHO's authentic single-observation preview and the independently validated Sentinel-1 diagnostic investigation remain useful pathways for advancing the application; each must retain its own source and QA status.

## Reproduction

Catalog screens:

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-10 --end 2026-11-13 --maturity VALIDATED \
  --cmr-timeout-seconds 90 --query-window-days 4 \
  --output data/research/validated-gcov-global-time-series-2026-11-10-13.json
```

Repeat with `--maturity PROVISIONAL` and `--maturity BETA` to reproduce the two zero-scene catalog records. The exact QA summaries can be re-requested from the checksummed selection records and scene lists using `tools/research/screen_nisar_crid_reprocessing_qa.py` with `--summaries-only`; each selection manifest verifies its input record hash and exact selected scene set before provider requests begin.
