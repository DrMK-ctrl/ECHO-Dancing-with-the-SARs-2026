# Decision 0032: Retain the failed SMAP/Sentinel-1 surface-state candidate screen

**Date:** 2026-11-08
**Status:** Implemented for the T163 Rio Grande do Sul diagnostic case

## Decision

Retain an exact-AOI, two-date screen of NASA NSIDC SPL2SMAP_S Version 3 as a **quality-limited candidate screen**, not as an accepted soil-moisture measurement or independent SAR validation. Record its product identity, CMR granule identifiers, Harmony parameters, returned subsets, processing history, quality flags, and checksums. Link the result to the alternative-surface-driver hypothesis as `LIMITS_INTERPRETATION` and leave the independent evidence search open.

The product is an active-passive retrieval: it combines SMAP L-band radiometry with Sentinel-1 C-band backscatter. Its 3 km field is validated at product level, but this case's exact-AOI cells fail the product's per-cell quality checks. The earlier value also exceeds its reported valid range. The screen therefore contributes no surface-state measurement to ECHO's interpretation.

## Retrieved observations and quality result

The case AOI is `[-51.24, -30.04, -51.23, -30.03]` WGS84. Harmony returned one intersecting 3 km EASE-Grid cell per date on the same grid:

The retained geometry check transforms the AOI into EPSG:6933 and intersects it with the posted 3002.69 m cell polygon. The one cell covers 100% of the AOI; the AOI covers 11.86% of the much larger cell. This confirms spatial support for the requested point-scale screen while making the coarse footprint explicit. No resampling was performed.

- Before: `SMAP_L2_SM_SP_1AIWDV_20240509T084904_20240508T220709_051W30S_R19240_001.h5`, CMR concept `G3014364731-NSIDC_CPRD`. Its disaggregated soil-moisture value is `1.1492 cm³/cm³`, above the product `valid_max` of `0.75`; retrieval flag `199` and surface flag `6157` are nonzero.
- After: `SMAP_L2_SM_SP_1AIWDV_20240602T084904_20240601T220657_051W30S_R19240_001.h5`, CMR concept `G3068710176-NSIDC_CPRD`. Its value is within numeric range, but retrieval flag `65` and surface flag `6157` are nonzero.

Neither cell has `retrieval_qual_flag_3km == 0`; both have the overall quality-compromised bit and degraded disaggregated-brightness-temperature bit set. The pair has **zero quality-eligible cells**. The same-grid result is exact; no resampling or interpolation was performed.

The `SMAP_Sentinel_overpass_timediff_hr_3km` field name and NSIDC documentation describe a time difference in hours, while the returned NetCDF units attribute says seconds. The raw value is retained without conversion and is not used to make a temporal claim.

## Interpretation

This candidate was worth screening because it offers SMAP passive-radiometer information at a nominal 3 km posted grid. It does not provide usable evidence here: the cells fail product QA, and the derived product also uses Sentinel-1 input. ECHO does not display its values as a measurement layer or use them to explain the OPERA response. The H3 alternative-driver hypothesis remains `UNRESOLVED` and `NOT_TESTED`; a suitable independent source is still needed.

## Reproduction and provenance

With local Earthdata Login in `~/.netrc`, reproduce the bounded CMR and Harmony retrieval and record with:

```bash
.venv/bin/python tools/research/screen_smap_s_candidates.py \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --bbox=-51.24,-30.04,-51.23,-30.03 \
  --before-date 2024-05-09 --after-date 2024-06-02 \
  --before-granule SMAP_L2_SM_SP_1AIWDV_20240509T084904_20240508T220709_051W30S_R19240_001.h5 \
  --after-granule SMAP_L2_SM_SP_1AIWDV_20240602T084904_20240601T220657_051W30S_R19240_001.h5 \
  --output-dir data/research/source-artifacts \
  --output-record data/research/smap-sentinel-soil-moisture-screen-T163-349925-2026-11-08.json
```

Rebuild the T163 assessment with the additional `--smap-screen-record` argument. The builder checks case/AOI identity, zero eligible cells, and both source-subset checksums; the web application repeats checksums before exposing the linked source record.

## References

- [NSIDC SPL2SMAP_S Version 3 dataset and DOI](https://nsidc.org/data/spl2smap_s/versions/3), DOI `10.5067/ASB0EQO2LYJV`.
- [NSIDC SPL2SMAP_S Version 3 User Guide](https://nsidc.org/sites/default/files/spl2smap_s-v003-userguide_0.pdf), sections 2.6.4.1 and 2.6.4.3.
- [NASA Harmony documentation](https://harmony.earthdata.nasa.gov/docs).
