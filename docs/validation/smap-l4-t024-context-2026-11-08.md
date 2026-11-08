# NASA SMAP L4 regional context screen for T024 — 2026-11-08

## Result

Authenticated NASA Harmony bounded reads and exact-day CMR searches succeeded for the T024 SAR dates. The selected product is NASA NSIDC SPL4SMAU Version 8. The source is linked to H3 as non-distinguishing model context; it is not treated as an independent or AOI-resolving soil-moisture observation. H3 remains unresolved and not testable with the retained evidence.

## Source and retrieval evidence

| SAR target UTC | Selected CMR granule | Analysis UTC | Offset | CMR concept |
|---|---|---|---:|---|
| 2024-05-11 08:49:47 | `SMAP_L4_SM_aup_20240511T090000_Vv8012_001.h5_I5bjLDJh` | 2024-05-11 09:00:00 | 10.22 min | `G4351816611-NSIDC_CPRD` |
| 2024-06-04 08:49:46 | `SMAP_L4_SM_aup_20240604T090000_Vv8012_001.h5_I5bjLDJh` | 2024-06-04 09:00:00 | 10.23 min | `G4351841448-NSIDC_CPRD` |

CMR returned 9 exact-date granules on each requested date; each screen retained all returned results and confirms the result count equals `CMR-Hits`. Harmony returned a bounded 3 by 3 native-grid window for each date in NetCDF-4, 81,507 bytes each. The product collection concept is `C3480440639-NSIDC_CPRD`; DOI `10.5067/02LGW4DGJYRX`.

The bounded subset assets are:

- `data/research/smap-l4-t024-context/smap-l4-rio-grande-do-sul-cross-sensor-diagnostic-2024-before-2024-05-11-bounded.nc4` — SHA-256 `49151ca39d2d9c909ff3e4cdb956fe2591905db4f60e660b0f9c42768238a8de`
- `data/research/smap-l4-t024-context/smap-l4-rio-grande-do-sul-cross-sensor-diagnostic-2024-after-2024-06-04-bounded.nc4` — SHA-256 `2b3b1faeef84baefb347f364571d045eb1d02541d9665401b7810b62fb3ec69a`
- Screen record `data/research/smap-l4-regional-context-T024-050661-2026-11-08.json` — SHA-256 `909b57452148fdf225f0d18bbf53533a6b7b1bac7996e846791ede8d501e9fae`

The screen records source identity, original CMR query URLs and response hashes, acquisition and retrieval times, exact Harmony parameters and history, CRS, native coordinates, variables and units, cell-grid hash, subset sizes and checksums, and the comparison method. No credentials or signed URLs are retained.

## Scientific review

At the same nearest grid cell for both dates (center `(-51.208508, -30.026934)`, about 2.70 km from the AOI center), the model analysis is 0.385752 m³/m³ before and 0.389290 m³/m³ after. The descriptive difference is 0.003538 m³/m³. Ensemble standard deviations are 0.013692 and 0.018409 m³/m³. All valid cells, not only the nearest one, share the same native coordinate grid; no resampling was performed.

Both horizontal and vertical assimilated brightness-temperature and observation-time fields are fill values in all six returned spatial cells on both dates. The product still represents model output informed by satellite assimilation; these local fill values do not establish the absence of SMAP inputs at other locations or times. The 9 km grid is much coarser than the approximately 1 km AOI. Because NSIDC documents IMERG Final V07 precipitation forcing for this region, this product is not independent corroboration of the linked GPM chronology. Ensemble spread is not treated as product QA or as a significance threshold; no uncertainty covariance or significance test was computed.

## Reproduction

With local Earthdata credentials available through the user's configured `.netrc`, retrieve and build with:

```bash
.venv/bin/python tools/research/screen_smap_l4_context.py \
  --case-id rio-grande-do-sul-cross-sensor-diagnostic-2024 \
  --bbox=-51.24,-30.04,-51.23,-30.03 \
  --before-time 2024-05-11T08:49:47Z \
  --after-time 2024-06-04T08:49:46Z \
  --output-dir data/research/smap-l4-t024-context \
  --output-record data/research/smap-l4-regional-context-T024-050661-2026-11-08.json
```

Rebuild the active assessment with the command documented in [Decision 0073 validation](gpm-t024-investigation-link-2026-11-08.md), adding:

```bash
--smap-l4-context-record data/research/smap-l4-regional-context-T024-050661-2026-11-08.json
--output data/research/opera-rtc-cross-sensor-investigation-2026-11-08-temporal-series-gpm-smap-l4.json
```

The case manifest selects that new assessment and keeps the prior assessment file. The builder reopens both NetCDF subsets, checks their hashes and grid identity, reproduces recorded arrays and selected-cell values, and rejects a directional hypothesis link or QA promotion.

## Verification

- `tests/test_smap_l4_context.py` — CMR nearest-time selection, time-limit rejection, native field/fill preservation, and Harmony granule-history checks.
- `tests/test_cross_sensor_investigation.py` — assessment linkage, checksum-backed native-grid reproduction, non-distinguishing H3 relation, and retained open test design.
- `tests/test_web.py::test_t024_active_assessment_validates_sar_and_rainfall_context_relationships` — active case assessment and its linked source assets.
- Broader suite results are retained in the development commit and should be refreshed after integration.
