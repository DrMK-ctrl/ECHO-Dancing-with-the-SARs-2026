# Iraq NISAR QA-held single-observation preview

**Browser:** Firefox headless, local interactive workbench
**Observation:** 2026-10-25 02:10:15 UTC, ascending path 13/frame 18, P05036
**Disposition:** `QA_HELD_DIAGNOSTIC_PREVIEW`

## User-facing path

In Firefox, ECHO searched the Iraq WGS84 area, selected the October 25
observation, and loaded one bounded frequency-A `HHHH` layer. A 0.2° rectangle
was rejected by the interactive 65,536-sample limit before any pixel window
was read; the interface instructed the user to draw a smaller area. With the
0.05° rectangle `[44.60, 33.20, 44.65, 33.25]`, the bounded read completed and
the map rendered a raster preview. The map caption identified `NISAR HHHH
backscatter preview · product QA FAIL`.

The inspector labeled this **REAL NISAR GCOV · QA-HELD DIAGNOSTIC PREVIEW**,
stated that it is one acquisition and not a change measurement or event
interpretation, and exposed the product identity, acquisition UTC, QA summary
hash, layer, CRS, display screen, and access provenance.

## Retained measurements and checks

- Product: `NISAR_L2_PR_GCOV_034_013_A_018_2005_DHDH_M_20261025T021015_20261025T021050_P05036_N_F_J_001`
- Provider QA: `FAIL`; canonical 1,441-byte summary SHA-256
  `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`.
- Window: 278 × 234 samples in EPSG:32638; 64,567 pixel centers inside the
  requested WGS84 bounds, with 50,370 display-eligible values.
- Display: linear gamma-zero power, transformed to `10 log10` dB for display
  only, stretched from −14.24 to −4.15 dB using the 2nd–98th percentiles of
  eligible AOI samples.
- Retrieval: 9,602,978 HTTPS byte-range bytes; no complete HDF5 download.
- Current-source API replay: a fresh bounded read on the current source returned
  the same provider-QA and HHHH array hashes, with 50 range requests over
  77.75 seconds. This confirms the current code records range count and fetch
  time for this real-data path; the existing port-8766 workbench process was
  started before those source changes and its retained UI response did not
  include per-request timing. The user-owned service was left running.
- SHA-256 checks for HHHH, mask, number of looks, exception mask, both
  coordinate vectors, and the exact AOI-selection mask all recompute from the
  retained record.

The 11,639,276-byte reproduction record, including the bounded values,
quality layers, projected coordinates, WGS84 pixel corners, checksums, QA
summary, and read provenance, is
[`2026-11-13-iraq-nisar-p05036-diagnostic-preview.json`](../../data/research/2026-11-13-iraq-nisar-p05036-diagnostic-preview.json).
Manifest SHA-256:
`60bc2427a031f68eb93bf15d42d243d7807842e4049128ce66e1f199f9f60792`.

## Scientific limit

This preview does not change either product's QA status and does not qualify
the pair for temporal analysis. The provider identification-group failure
remains decisive; the preview is retained only to inspect authentic single-date
measurements and their documented masks. No event, cause, damage, or surface
change is inferred.
