# Istanbul flooding — NISAR candidate review

**Reviewed:** 2026-11-07 UTC  
**Disposition:** Candidate only; both selected products remain on `QA_HOLD`  
**Raster analysis:** None performed

## Event context

The Disaster and Emergency Management Authority of Türkiye (AFAD), through the Asian Disaster Reduction Center, requested international assistance for flooding in Türkiye. The International Charter activation describes torrential rain and flash flooding on 14–15 October 2026 and includes a 20 October product titled “Potential Flood-Affected Areas in Ayazaga.” Sentinel Asia records the same emergency observation request and lists a Sentinel-1-derived affected-area product for Ayazaga observed on 18 October. These records establish event context and provide a possible independent satellite-derived comparison layer; they are not field truth for any ECHO result.

## NISAR catalog evidence

A live ASF query was run for an approximate Ayazaga point (28.990° E, 41.105° N), 1–31 October 2026, PROVISIONAL GCOV. The saved catalog snapshot contains six features and three metadata-level temporal candidates. One candidate brackets the reported event:

| Role | Acquisition (UTC) | Orbit | Scene |
|---|---|---:|---|
| Before | 2026-10-09 17:04:32 | 6291 | `NISAR_L2_PR_GCOV_032_137_D_068_2005_DHDH_A_20261009T170432_20261009T170506_P05023_N_F_J_001` |
| After | 2026-10-21 17:04:32 | 6464 | `NISAR_L2_PR_GCOV_033_137_D_068_2005_DHDH_A_20261021T170432_20261021T170507_P05023_N_F_J_001` |

Both are in the same PROVISIONAL GCOV collection, CRID `P05023`, path 137/frame 68, descending, 20+5 MHz, dual HH/HV polarization, and their catalog footprints intersect. The acquisitions are 12 days apart. This is metadata compatibility only; it does not establish study-area coverage at pixel level, valid-data overlap, registration, or change.

## Product QA and provenance

For both products, authenticated HDF5 metadata reads recorded `instrumentName=LSAR`, `listOfObservationModes=["(NOT SPECIFIED)"]`, product specification version `1.5.0`, product version `1.0.11`, frequencies A/B, and the expected orbit/track/frame. Each bounded read requested 30,416,925 bytes of HTTP ranges; no measurement array or full product was read.

The two canonical ASF QA summary artifacts were retrieved separately on 2026-11-07 and each returned 1,441 bytes with SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`. Both report `FAIL` for “Passes all identification group checks?” and `PASS` for input opening, coordinate-grid metadata, calibration LUT metadata, four decimated backscatter checks, and QA completion without exceptions. The two QA report PDFs have distinct hashes and identify QA software 17.0.0, with processing times 2026-10-11 20:26:15 UTC and 2026-10-23 13:00:13 UTC. Their observed identification values are captured in the linked local records.

The exact `nisarqa` v17.0.0 source accepts `L-SAR`/`S-SAR` and validates observation modes against a documented format. Thus the observed strings match source-rule conditions associated with identification failure. ECHO records this as a partial diagnostic cross-check; it does not establish that these are the only failed fields, replace the provider disposition, or establish whether the pixels are suitable. The product-specification 1.5.0 XML describes these fields and their shapes but does not enumerate the same value constraints. A provider or specification reconciliation remains necessary. A public GCOV issue separately reports a `(NOT SPECIFIED)` placeholder, which corroborates a known issue type, not the state of these two granules.

## What this candidate can support now

- Event occurrence and timing are supported by the official activation record and Sentinel Asia request record.
- A post-event Sentinel-1 product is listed for Ayazaga, offering a possible independent satellite-derived comparison source whose method, exact geometry, and licensing still need review.
- ASF metadata identifies a plausible NISAR before/after acquisition pair over the search point.
- The provider QA evidence currently prevents ECHO's paired measurement function from accepting either product.
- No NISAR pixels have been compared. ECHO has produced no flood boundary, change map, area estimate, damage assessment, or causal finding.

The candidate is visually and temporally promising, but it is not yet a scientifically usable demonstration. Reconcile QA first, then establish the actual AOI coverage, masks, common valid pixels, grid alignment, and a predeclared event/control measurement design. Review the Sentinel Asia map as an independent derived product, not as ground-truth labels.

## Local evidence records

- [`case-review.json`](../../data/cases/istanbul-2026/case-review.json) — event context, catalog query, pair, QA disposition, cross-checks, and open gates.
- [`catalog.json`](../../data/cases/istanbul-2026/catalog.json) — ASF metadata snapshot; no pixels.
- [`identification-before.json`](../../data/cases/istanbul-2026/identification-before.json) and [`identification-after.json`](../../data/cases/istanbul-2026/identification-after.json) — bounded authenticated HDF5 identification reads.
- [`qa-summary-before.json`](../../data/cases/istanbul-2026/qa-summary-before.json) and [`qa-summary-after.json`](../../data/cases/istanbul-2026/qa-summary-after.json) — row-preserving summary parses, source URIs, retrieval timestamps, checksums, and validator cross-checks.
- [`istanbul-interface-2026-11-07.png`](../validation/istanbul-interface-2026-11-07.png) — local Firefox rendering of the pinned pair, metadata-only footprint view, and QA hold.

## References

- International Charter: Space and Major Disasters, [Flood in Türkiye, Activation 1055](https://download.disasterscharter.org/activations/flood-in-t%C3%BCrkiye-activation-1055-).
- Sentinel Asia, [Flood in Istanbul, Türkiye, 14 October 2026](https://sentinel-asia.org/EO/2026/article20261014TR.html).
- NASA JPL, [NISAR L2 GCOV Product Specification, Revision F](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf).
- `nisarqa` [v17.0.0 release](https://github.com/isce-framework/nisarqa/releases/tag/v17.0.0), [tagged identification checks](https://github.com/isce-framework/nisarqa/blob/v17.0.0/src/nisarqa/validate/sanity_checks.py), and [GCOV product-specification 1.5.0 XML](https://github.com/isce-framework/nisarqa/blob/v17.0.0/src/nisarqa/product_specs/1.5.0/nisar_L2_GCOV.xml).
- ISCE3, [GCOV dataset and attribute issues #216](https://github.com/isce-framework/isce3/issues/216) — includes a separate GCOV sample with a `(NOT SPECIFIED)` observation-mode value; its many other reported findings were disputed as potential false positives.
