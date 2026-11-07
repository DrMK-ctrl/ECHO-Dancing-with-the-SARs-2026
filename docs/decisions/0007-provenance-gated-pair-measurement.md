# Decision 0007: provenance-gated paired-window measurement

**Date:** 2026-11-07  
**Status:** Implemented for bounded windows; synthetic validation only

## Context

ECHO has a reusable bounded GCOV reader, projection metadata, coordinate vectors, and low-level mask and log-ratio primitives. Those components need a controlled join that refuses held products and records how a derived measurement depends on its source windows.

## Decision

Add `analyze_gcov_pair` as the first product-to-measurement integration point. Require a reviewed `PASS` QA receipt for each exact scene, with a source URI and SHA-256. Require compatible ASF collection, processing level, CRID, production configuration, path/frame, direction, bandwidth, polarizations, and acquisition chronology. Decision 0008 further requires distinct known NISAR orbits and nonoverlapping acquisition intervals. Require matching frequency, array indices, EPSG, projection value, and exactly equal X/Y pixel-center coordinates for the selected windows.

Use the strict common mask from both dates, require positive finite number-of-looks values on every common-valid sample, and compute the descriptive signed GCOV power log ratio. Record source catalog and product metadata, QA artifact references and subchecks, retrieval records, checksums of selected input windows, masks and output values, coordinate references, look-count summaries, method, and software versions in a checksummed manifest.

## Evidence and limits

- 45 offline tests pass, including synthetic measurements, QA-hold refusal, placeholder product-identification rejection, catalog identity mismatch refusal, incompatible CRID refusal, coordinate mismatch refusal, and manifest checksum verification.
- No QA-held ECHO case has been passed to this function. The current Nepal and Mozambique products still fail their identification-group QA check.
- The October authenticated window probe verified real product retrieval and grid metadata only. It did not exercise the pair-analysis function with real pixels.
- QA receipts preserve the reviewed status and artifact hash; the function does not execute the NASA/ASF QA validator or independently hash the referenced report. The caller must supply a correct reviewed receipt.
- Exact sampled coordinate equality supports registration only for the selected window. It says nothing about unsampled pixels or geolocation accuracy.
- Window hashes cover the selected arrays and coordinate vectors, not the complete multi-gigabyte source HDF5 file.
- The log ratio is descriptive. The function does not classify an event, infer cause, calculate statistical significance, or estimate confidence.

## Consequences and open work

- Any caller using this API must provide QA evidence and compatible windows; data access alone cannot clear a QA hold.
- The manifest gives future source-inspection UI and reproducible export a stable input/output lineage record.
- Current products cannot yet yield a valid real-data run. The next scientific gate remains QA reconciliation or replacement by a suitable pair, followed by a bounded real-data run and independent evaluation.
- Geographic AOI selection, registration beyond exact sampled coordinate equality, event/control strata, persistent result storage, and UI integration remain open.

## References

- ASF, [Geocoded Polarimetric Covariance (GCOV)](https://nisar-docs.asf.alaska.edu/gcov/).
- NASA JPL, [NISAR L2 GCOV Product Specification, Rev F](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf).
- ECHO, [GCOV log-ratio measurement decision](0004-gcov-log-ratio-measurement.md).
- ECHO, [bounded GCOV window access decision](0005-bounded-gcov-window-access.md).
- ECHO, [GCOV grid metadata decision](0006-gcov-grid-metadata.md).
