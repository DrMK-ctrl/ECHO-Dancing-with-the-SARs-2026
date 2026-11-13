# VALIDATED GCOV full/full pair QA screen — 2026-11-13

## Question and scope

Could the retained global VALIDATED-GCOV temporal candidates provide a metadata-compatible, full/full P05036 pair whose exact-product provider QA summaries clear the first quality gate?

The source catalog is [`validated-gcov-global-time-series-2026-10-09-11-08.json`](../../data/research/validated-gcov-global-time-series-2026-10-09-11-08.json), containing 2,018 unique scenes and 54 metadata pair candidates. Thirty-nine are full/full pairs. An exact-product QA inventory across the retained local `data/**/*.json` records found eight of those pairs already had both product summaries and no partial pair had a retained exact summary. The selection therefore contains the remaining 31 full/full pairs and 62 product IDs. Partial-coverage pairs were excluded from this first pass because full/full candidates are the strongest available route to a bounded comparison.

The checksummed selection record documents the catalog, prior QA records, criteria, pairs, and exact product IDs: [`selection JSON`](../../data/research/validated-gcov-p05036-unscreened-full-pair-selection-2026-11-13.json). The companion scene list is [`selection input`](../../data/research/validated-gcov-p05036-unscreened-full-pair-scene-ids-2026-11-13.txt).

## Retrieval and result

ECHO retrieved each product's canonical ASF QA-summary CSV only. The bounded screen returned all 62 summaries successfully, each 1,441 bytes. No QA report PDFs, HDF5 metadata, raster arrays, masks, or pixel measurements were retrieved; no spatial-grid or temporal comparison was performed.

- Provider summary disposition: **62/62 FAIL**.
- Aggregate identification group: **62/62 FAIL**.
- All other eight reported checks: **62/62 PASS** for each applicable check (input open, coordinate-grid metadata, calibration LUT, four decimated backscatter checks, and QA completion).
- Retrieval errors: **0**.
- Summary artifact checksums: 58 products share SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`; four products share SHA-256 `fac34ec88c3863ec6c7b09e19eb88e527d41472f23fcbed58e1cc9de98d79b75`. The four-product subset comprises the Oct 23 and Nov 4 path 156/frame 7 DVDV products and the Oct 25 and Nov 6 path 19/frame 78 DVDV products; all four also fail only the aggregate identification group in their summaries.

The full machine-readable product records, per-product retrieval timestamps, catalog linkage, and exact scene list are in [`QA screen JSON`](../../data/research/validated-gcov-p05036-unscreened-full-pairs-qa-2026-11-13.json), SHA-256 `488c6a365890efd6c91b2760cefc0d630559a45a92837e89fda24ece2646bca4`. The record identifies the selection input by SHA-256 `924ed95ac01bfee4ac70d1762207e9069755b00cfa486912ecfedc430f7b9685` and the selection-manifest record by SHA-256 `5966d1d5cd3d540b2552742d8847a18f77d8d53d0346ee889d7f377ec975c0c8`.

Reproduce the bounded screen with:

```bash
.venv/bin/python tools/research/screen_nisar_crid_reprocessing_qa.py \
  --catalog data/research/validated-gcov-global-time-series-2026-10-09-11-08.json \
  --case-id validated-gcov-p05036-unscreened-full-pairs-2026-11-13 \
  --crid P05036 \
  --scene-id-file data/research/validated-gcov-p05036-unscreened-full-pair-scene-ids-2026-11-13.txt \
  --selection-manifest data/research/validated-gcov-p05036-unscreened-full-pair-selection-2026-11-13.json \
  --summaries-only \
  --output data/research/validated-gcov-p05036-unscreened-full-pairs-qa-2026-11-13.json
```

## Interpretation boundary

This closes the unscreened full/full subset in this retained global catalog; it does not establish that all P05036 products, all VALIDATED dates, or all NISAR maturities fail QA. ASF's CSV exposes only the aggregate identification-group result and does not attribute it to individual metadata fields. The four-product different-checksum subset does not change that limitation. Previous PDF reviews found partial `nisarqa` source-rule mismatches for instrument and observation-mode values, but those cross-checks do not explain ASF's aggregate dispositions.

No candidate in this full/full set can proceed to ECHO's paired measurement path under the current provider-QA gate. Do not infer a change result from these QA summaries or treat the repeated QA outcome as evidence about surface change.

## Supplemental partial-coverage candidate screen

The same retained catalog contains 15 additional metadata candidates where at least one product has partial frame coverage. Since partial catalog coverage does not by itself rule out a smaller AOI-specific overlap, the 15 pairs were screened separately rather than assumed unsuitable. No exact canonical QA summary for either scene in these pairs was found in the retained local records before retrieval. ECHO retrieved the 30 exact ASF CSVs; all returned without error. All 30 summaries report aggregate identification-group `FAIL`; every other check present in each summary reports `PASS`. Twenty-six CSVs are 1,441 bytes and four are 5,927 bytes. The different payload sizes and hashes do not change the reported disposition.

The checksummed selection and scene list are [`partial-pair selection`](../../data/research/validated-gcov-p05036-partial-pair-selection-2026-11-13.json) and [`scene IDs`](../../data/research/validated-gcov-p05036-partial-pair-scene-ids-2026-11-13.txt). The exact products and provider responses are in [`partial-pair QA results`](../../data/research/validated-gcov-p05036-partial-pairs-qa-2026-11-13.json), SHA-256 `e08f27dd378d4b4b000c6ec3d036590a47f5bd5da588c2aa0fc1f66ea48da3c4`. Its selected scene-list SHA-256 is `2529a9f7ef1dfd45d5744a3d1c8e24d163f8b49e2242039c25c2cb5787c9078c`; the selection-manifest SHA-256 is `e3c30a04cb51217a641cfee0af4f409564eb87a48d8826dabe6bb6d1bd5229b0`.

Across all 54 candidates in this bounded catalog snapshot, all 108 products now have exact QA-summary evidence: the 78 products in 39 full/full pairs and 30 products in 15 partial-coverage pairs. All 108 report provider `FAIL` for the aggregate identification group. This closes QA-summary screening for this snapshot only. It does not establish that every NISAR product or P05036 release fails, and it does not identify the provider's failing field. No PDFs or radar arrays were retrieved for the two new batches, and no spatial or temporal measurements were computed.
