# NASA DSWx-HLS context map validation

The local ECHO interface can load the retained OPERA DSWx-HLS evidence record as a separate map mode. It renders the source class cells at their WGS84 pixel corners, lets the user switch between WTR, WTR-2, and CONF, switch acquisition dates, and click a cell to inspect its class code, native row/column, and geographic center. The source inspector exposes product identity, acquisition, CRS, class counts, retrieval status, and checksums.

This mode deliberately suspends the selected SAR case display while active. Closing it restores the previous case and map. DSWx-HLS remains optical HLS-derived context, not a SAR measurement, field observation, or independent validation of an RTC-S1 result.

## Source and processing

- Provider: NASA PO.DAAC, OPERA L3 DSWx-HLS Version 1.
- Earlier product: `OPERA_L3_DSWx-HLS_T22JDM_20240508T132241Z_20240510T085001Z_S2A_30_v1.0`, acquisition 2024-05-08 13:30:53.463 UTC.
- Later product: `OPERA_L3_DSWx-HLS_T22JDM_20240602T132239Z_20240604T152339Z_S2B_30_v1.0`, acquisition 2024-06-02 13:30:52.554 UTC.
- AOI: `[-51.24, -30.04, -51.23, -30.03]` WGS84; 1,199 selected native pixel centers on EPSG:32622.
- Four class assets per acquisition were read through bounded HTTPS byte ranges. Retrieved byte counts and MD5 values matched CMR; SHA-256 values and acquisition metadata are preserved in the [machine-readable record](../../data/research/dswx-hls-rtc-aoi-context-2026-11-07.json).
- The record contains 1,199 derived map cells with native WTR, WTR-2, CONF, and CLOUD codes and WGS84 cell corners. Full source rasters are not stored. Recreate the evidence record using [`evaluate_dswx_hls_aoi.py`](../../tools/research/evaluate_dswx_hls_aoi.py) and the exact granule identifiers in the JSON.
- Evidence-record SHA-256: `8ff957f11ae7113e25609b93eabcddb7344a2d09492bd5b6ecd19ae14ba23479`.

The WTR transition summary remains 837 common valid cells, with water-class counts 36 before and 27 after. WTR-2 has 1,199 common cells, with water-class counts 135 before and 59 after. In the earlier WTR-2 product, 99 of 135 water-coded cells carry cloud or snow/ice flags in CONF; in the later product, 2 of 59 do. These are product class counts, not a flood-boundary validation or a conclusion about the physical cause. CONF is a confidence and quality-context layer, not a second independent water classification.

NASA's [DSWx-HLS Product Specification](https://d2pn8kiwq2w21t.cloudfront.net/documents/OPERA_DSWx-HLS_ProductSpec_v1.0.0_D-107395_RevB.pdf) defines the product layers and class meanings. NASA Earthdata's [Brazil DSWx-HLS map metadata](https://gis.earthdata.nasa.gov/portal/rest/services/DISASTERS_EX2602_202405_FLOOD_BRAZIL/EX2602_opera_dswx_hls/MapServer) also documents WTR categories and limitations such as cloud masking and snow/ice labeling.

## Verification

- Full project test suite: 180 passed, including the DSWx evaluator and web-route coverage.
- Python compilation and `git diff --check`: passed.
- Firefox/geckodriver local browser check: loaded 1,199 cells; switched to CONF and the later acquisition; clicked a cell and confirmed the NASA source, date, native cell, and class value in the inspector; hid the context view and confirmed the original Istanbul case returned with no context polygons left on the map.
- Captured state: [map screenshot](dswx-context-map-2026-11-07.png).
- Screenshot SHA-256: `434fb28f7168d01da44cf9e2a77da879ea1f7c6081e2f7cf615e39c751e24f11`.

The UI check validates software wiring and presentation. It does not independently validate DSWx-HLS classification accuracy or the scientific interpretation of the OPERA RTC-S1 measurement.
