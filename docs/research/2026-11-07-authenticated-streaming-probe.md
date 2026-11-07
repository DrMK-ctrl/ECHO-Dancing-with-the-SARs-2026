# Authenticated NISAR window-read probe — 2026-11-07

## Purpose

Verify Earthdata-authenticated, range-based access to a small NISAR GCOV area without downloading a complete multi-gigabyte product. This is an ingestion/access check only; it is not a flood assessment or change analysis.

## Observation and request

- Provider: Alaska Satellite Facility NISAR archive.
- Product: `NISAR_L2_PR_GCOV_033_114_A_165_4005_DHDH_A_20261020T034212_20261020T034250_P05023_N_F_J_001`.
- Catalog maturity: `PROVISIONAL`.
- Catalog search point: 33.5° E, 24.5° S.
- Projected center: EPSG:32736, easting 550657.546 m, northing 7290323.026 m.
- Requested coordinate-center window: ±500 m around that point, index rows `[9998, 10098)` and columns `[22040, 22140)`, giving 100 × 100 samples.
- The product grid reported EPSG:32736 and 10 m x spacing / -10 m y spacing.

## Result

Earthdata authentication from the local `netrc` succeeded. The authenticated HTTPS range stream opened the HDF5 product and `/science/LSAR/GCOV/grids/frequencyA`; it returned the requested 100 × 100 slices for:

| Dataset | Observed window dtype |
| --- | --- |
| `HHHH` | `float32` |
| `HVHV` | `float32` |
| `mask` | `uint8` |
| `numberOfLooks` | `float32` |
| `inputDataExceptionMask` | `uint8` |

No full product was requested. Window values were read into memory for this probe, but no value distributions, pairwise differences, flood extent, or physical interpretation were calculated. No pixel arrays or credentials are stored in the repository.

## Evidence limits

The product's downloaded QA summary reports failure of the identification-group check. Keep the scene on QA review hold. The product specification defines the GCOV mask as a fully-focused subswath validity mask and the input-data exception layer as bitwise-OR exception codes; decoding or treating either layer as proof of pixel validity requires version-specific review. This probe does not establish alignment with another acquisition, common valid coverage, calibration quality, or a scientific finding.

## Reproduction outline

Use the live ASF catalog record for the exact scene; authenticate with `earthaccess.login(strategy="netrc")`; obtain the authenticated HTTPS filesystem using `earthaccess.get_fsspec_https_session()`; open the URL as a ranged file object; access the frequency-A HDF5 group; transform the query point to EPSG:32736; select the inclusive coordinate-center bounds ±500 m; and read only the five listed 100 × 100 slices. Do not print, commit, or transmit Earthdata credentials.

The official ASF Earthaccess guide documents authenticated HTTPS streaming with `earthaccess`, `fsspec`, and `h5netcdf`. The GCOV guide documents the covariance, number-of-looks, and mask layers. The current case QA hold remains controlling even though a small window is technically readable.

## Reproduction through the ECHO reader

The same request was repeated through `echo.nisar_access.read_gcov_window` after it was added as a reusable bounded API. A fresh exact-granule ASF search returned one feature. The helper read only the four layers shown above and the requested 100 × 100 slices; it reported 27,978,510 HTTPS range bytes requested, against its 67,108,864-byte cap. The returned arrays occupied an estimated 100,000 bytes. This validates the reader's access path on one real product, not the values or their suitability for an analysis.

```python
import asf_search as asf
from echo.nisar_access import read_gcov_window

scene_id = "NISAR_L2_PR_GCOV_033_114_A_165_4005_DHDH_A_20261020T034212_20261020T034250_P05023_N_F_J_001"
features = asf.search(granule_list=[scene_id], dataset="NISAR")
window = read_gcov_window(
    features.geojson()["features"][0],
    frequency="A",
    rows=slice(9998, 10098),
    columns=slice(22040, 22140),
)
```

The caller supplies array indices; this API does not yet derive them from a geographic region or read co-registration metadata. It does not run the log-ratio primitive, decode the masks for analysis, or assess QA. The scene's suitability for scientific use remains unestablished.

## References

- ASF NISAR Earthaccess streaming guide: <https://nisar-docs.asf.alaska.edu/earthaccess/>
- ASF NISAR GCOV layers and product description: <https://nisar-docs.asf.alaska.edu/gcov/>
- ASF NISAR pre-calibration known issues: <https://nisar-docs.asf.alaska.edu/product-known-issues/>
