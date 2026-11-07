# Nepal AOI candidate QA-summary screen

**Screened:** 2026-11-07

**Outcome:** No provider-QA-cleared pair among the candidate scenes screened

## Scope and method

The source is the live ASF PROVISIONAL GCOV AOI query for WGS84 bounds `(85.545, 28.295, 85.555, 28.305)`, acquisition dates August 1 through November 7, 2026. The catalog snapshot is [`kathmandu-aoi-catalog-query-2026-11-07.json`](../../data/research/kathmandu-aoi-catalog-query-2026-11-07.json), queried at `2026-11-07T06:06:49.954798Z`, with SHA-256 `b9481a83877fbb2c6168dc9379b9211a71f19505f2bed0edf7cea1cff2cafb07`.

The catalog produced nine metadata candidate pairs involving 13 unique granule IDs. ECHO retrieved each canonical ASF QA-summary CSV using `echo.qa.read_qa_summary`, Earthdata Login from the local netrc, and bounded authenticated HTTPS byte-range reads. The run covered `2026-11-07T06:32:08.144876Z` through `2026-11-07T06:33:09.306871Z`. Per-scene source and result records are in [`kathmandu-candidate-qa-screen-2026-11-07.json`](../../data/research/kathmandu-candidate-qa-screen-2026-11-07.json). Credentials and raster arrays were not stored.

## Results

- Provider disposition: **13 FAIL, 0 PASS, 0 INDETERMINATE**.
- All 13 summaries failed `Passes all identification group checks?`; every other check row in the summaries was reported PASS.
- The 13 product URLs yielded only two unique CSV payload hashes: 11 records share SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688` (1,441 bytes), and two share SHA-256 `48a023399b1f27d45925a03c13718c60e22eecfee52181191b5b37649510bc0d` (5,927 bytes). Therefore the screen is 13 product-URL observations of provider artifacts but only two distinct byte payloads, not 13 independent QA payloads.
- The source query contains several repeat-date and alternate-release records. The screen does not treat those as additional independent evidence or as a complete acquisition history.

ASF describes GCOV as calibrated gamma-0 power products, and its catalog's provider-generated QA summaries remain the controlling quality evidence for these candidate products. The [NISAR QA software](https://github.com/isce-framework/nisarqa) verifies product metadata against the product specification and emits product-quality reports; the upstream [v17.2.0 release](https://github.com/isce-framework/nisarqa/releases/tag/v17.2.0) identifies a version referenced in a separate validated-product review. The observed QA disposition is recorded without overriding it.

## Limits and decision

This screen supplied empty product-identification metadata to the parser because it retrieved QA summaries only; it did not independently re-read each product's HDF5 identification datasets. It does not establish the cause of the failures, whether those failures affect the gamma-0 layers, whether the event AOI has common valid pixels, or whether the products are aligned. QA summaries report aggregate checks; the hashes show duplicate payload bytes but do not establish how the provider generated or associated each file.

Keep all screened scenes on provider QA hold. Do not run paired measurement on these products or reinterpret the repeated CSV payloads as a waiver. Next useful evidence is a provider disposition for the exact identification failures or a different scientifically compatible pair whose per-product provider QA passes. No NISAR pixel arrays were retrieved or analyzed in this screening; it produced no change estimate or event finding.

## Reproduction

```python
import json
from echo.qa import read_qa_summary

catalog = json.load(open("data/research/kathmandu-aoi-catalog-query-2026-11-07.json"))
features = {f["properties"]["fileID"]: f for f in catalog["features"]}
scene_id = next(iter(catalog["metadata_candidate_pairs"]))["before_scene"]
qa = read_qa_summary(features[scene_id], product_metadata={})
print(qa.evidence.status, qa.evidence.checks, qa.artifact_sha256)
```

## References

- Alaska Satellite Facility, [NISAR GCOV product guide](https://nisar-docs.asf.alaska.edu/gcov/).
- isce-framework, [NISAR QA software and v17.2.0 release](https://github.com/isce-framework/nisarqa/releases/tag/v17.2.0).
- ECHO implementation: [`echo/qa.py`](../../echo/qa.py) and [`echo/catalog.py`](../../echo/catalog.py).
