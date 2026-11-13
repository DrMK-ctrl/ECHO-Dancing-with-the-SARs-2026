# Geographic GCOV window access validation

**Date:** 2026-11-07
**Result:** Access and geographic selection verified; scientific use not validated

## Observation

An Earthdata-authenticated HTTPS byte-range read retrieved the `HHHH` layer from NISAR L2 GCOV PROVISIONAL product `NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001` over a WGS84 rectangle `(85.545, 28.295, 85.555, 28.305)`. The product grid uses EPSG:32645. The selected enclosing window was 112 rows by 100 columns, containing 10,874 pixel centers inside the requested bounds. The reader fetched 21,407,117 remote range bytes, including 546,624 bytes for full coordinate vectors. The in-memory raster window and exact AOI mask are represented by SHA-256 digests in the [machine-readable record](../../data/research/geographic-window-access-2026-11-07.json); raster values were not saved.

## Quality disposition and limits

The retained ASF provider QA summary reports **FAIL** for “Passes all `identification` group checks?” This result was not waived. The read demonstrates authenticated access, CRS transformation, bounded selection, and provenance capture only. No raster values were summarized, compared, classified, or interpreted. This does not validate cross-date registration, common valid coverage, the measurement function on real NISAR data, or any event claim.

The recorded CRS transformation reports expected accuracy `-1.0` (unknown). The rectangular selection implements an inverse-transformed pixel-center inclusion rule; it is not a polygon rasterization or area-weighted selection. Antimeridian-crossing bounds are rejected.

## CRS accuracy metadata and high-latitude regression — 2026-11-13

PROJ uses `-1` to mean that a coordinate operation's expected accuracy is
unknown. The current selector now serializes that state as
`transform_expected_accuracy_m: null` with
`transform_expected_accuracy_status: "UNKNOWN"`; a nonnegative reported
accuracy remains numeric and is labeled `REPORTED`. The historical real-scene
record above retains its original `-1.0` value and checksum; it was not
rewritten.

The geospatial test suite also exercised numeric grid selection in UTM
EPSG:32636 and in north/south polar stereographic EPSG:3413/EPSG:3031 at
86° latitude. All three synthetic coordinate grids returned nonempty masks
that exactly matched independently inverse-transformed pixel-center membership
checks, with the expected CRS metadata. The full suite passed **503 tests**.
These are coordinate-transform regression tests, not SAR-product measurements
or evidence of polar NISAR coverage.

The GCOV preview regression also verifies that an unknown operation accuracy
survives in the preview's access/provenance record as JSON `null` plus the
`UNKNOWN` status, without introducing non-finite JSON values.

## Reproduction

Use the optional `nisar` dependency set and locally configured Earthdata Login credentials. Invoke `echo.nisar_access.read_gcov_window` with the cited catalog feature, frequency `A`, the stated `bounds_wgs84`, and `layers=("HHHH",)`. The API applies bounded coordinate-vector, sample, memory, and remote-range limits. It does not consult provider QA; the separate analysis gate remains responsible for rejecting non-PASS QA evidence.
