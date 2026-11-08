# NASA MOD13Q1 vegetation candidate screen — T163

Date: 2026-11-08
Case: `rio-grande-do-sul-t163-349925-diagnostic-2024`
Disposition: quality- and temporal-support-limited candidate; not a vegetation change test

## Product and search

- NASA LP DAAC Terra/MODIS MOD13Q1 Version 6.1, collection concept `C1748066515-LPCLOUD`, DOI [`10.5067/MODIS/MOD13Q1.061`](https://doi.org/10.5067/MODIS/MOD13Q1.061).
- Bounded CMR search used the exact T163 AOI `[-51.24, -30.04, -51.23, -30.03]` and SAR dates 2024-05-08 and 2024-06-01.
- The dates fall in the 2024-05-08–2024-05-23 and 2024-05-24–2024-06-08 composites. Tiles h13v11 and h13v12 intersect the AOI; four exact HDF granules were retrieved from NASA LP DAAC.
- NASA describes MOD13Q1 as a 16-day 250 m product. Its algorithm selects per-pixel observations within the period, and its per-pixel composite-day layer records which day was selected. Adjacent pixels can therefore represent different days. See the [NASA product DOI page](https://doi.org/10.5067/MODIS/MOD13Q1.061) and [Version 6.1 User Guide](https://lpdaac.usgs.gov/documents/621/MOD13_User_Guide_V61.pdf).

The source-screen record is [`mod13q1-vegetation-candidate-T163-349925-2026-11-08.json`](../../data/research/mod13q1-vegetation-candidate-T163-349925-2026-11-08.json). It records all four CMR granule identifiers, source URLs, acquisition periods, tile IDs, file sizes, hashes, the pair-record hash, native-grid transform, and each retained AOI pixel's raw NDVI, detailed QA, summary QA, selected composite day, and SAR-date offset.

| Composite period | Pixel centers | Valid NDVI | SummaryQA rank 0 | SummaryQA rank 1 | Land class 1 | Strictly accepted |
|---|---:|---:|---:|---:|---:|---:|
| 8–23 May | 21 | 19 | 5 | 13 | 0 | 0 |
| 24 May–8 June | 21 | 20 | 0 | 20 | 0 | 0 |

The first composite's selected pixel days are 14, 15, and 22 May, 6–14 days after the 8 May SAR acquisition. The later composite selects 1 and 7 June, 0–6 days after the 1 June SAR acquisition. All reported offsets are retained per pixel in the record.

## Method and result

No reprojection or resampling was used. GDAL mosaicked the two intersecting sinusoidal tiles per period, then extracted the exact AOI window while preserving the native 231.656 m grid spacing. AOI membership was evaluated at the native cell centers.

The strict screen requires valid NDVI, DetailedQA MODLAND class 0, pixel-reliability SummaryQA rank 0, land/water class 1, and no adjacent-cloud, mixed-cloud, snow/ice, or shadow flags on both dates. The thresholds follow NASA LP DAAC's MOD13 Version 6.1 guide. No pixel passed the paired screen. The NASA source masks also classify zero AOI centers as land on either date. Therefore ECHO did not compute NDVI change or an NDVI/SAR association.

This is a suitability result for this case and product pair. It does not imply a MODIS product failure: the product-level automatic-quality metadata say no automatic quality assessment is performed by the production element, so ECHO relies on the product's per-pixel QA layers for this screen rather than treating that product metadata as a scene-level pass.

## Investigation integration

The T163 assessment [`opera-rtc-cross-sensor-investigation-T163-349925-2026-11-08.json`](../../data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-08.json) links the MODIS screen to H4 (`VEGETATION_STATE_CHANGE`) as `LIMITS_INTERPRETATION`. H4 remains `UNRESOLVED` and `DESCRIPTIVE_ASSOCIATION_ONLY` based on the separate, sparse HLS associations. Follow-up F9 is now `RETRIEVED_QUALITY_LIMITED` and cites the MODIS screen. Neither the underlying Sentinel-1 pair's diagnostic QA disposition nor any other hypothesis changes.

## Reproduction

After downloading the four HDF files named and linked in the JSON record, run from the project root:

```bash
.venv/bin/python tools/research/screen_mod13q1_vegetation.py \
  --pair-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --source-hdf /path/to/MOD13Q1.A2024129.h13v11.061.2024153222252.hdf \
  --source-hdf /path/to/MOD13Q1.A2024129.h13v12.061.2024153222138.hdf \
  --source-hdf /path/to/MOD13Q1.A2024145.h13v11.061.2024162165137.hdf \
  --source-hdf /path/to/MOD13Q1.A2024145.h13v12.061.2024162165130.hdf \
  --output /tmp/mod13q1-vegetation-candidate.json
```

The tool queries NASA CMR to verify the supplied granules and requires `gdalbuildvrt`, `gdal_translate`, and the project Python dependencies. It downloads no data itself. The original HDF files are not stored in the repository; the recorded hashes allow a downloaded copy to be checked before running the screen.

Focused verification: `tests/test_modis_vi.py`, the T163 case-record checks, and the investigation/web tests. These verify QA decoding, date-offset handling, source linkage, strict exclusion, and the unchanged unresolved disposition.
