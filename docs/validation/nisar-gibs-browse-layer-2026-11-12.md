# NISAR GCOV browse backdrop — 2026-11-12

## Result

The map now lets users choose NASA MODIS optical context, the NASA GIBS NISAR Level-2 GCOV daily browse mosaic, or a coordinate grid without a raster backdrop. The selected mode and observation date are sent to NASA GIBS using WMS 1.1.1 in EPSG:4326. The NISAR selection requests `NISAR_L2_Geocoded_Polarimetric_Covariance` as PNG and is explicitly labeled **PROVISIONAL GCOV DAILY MOSAIC · BROWSE ONLY**. The About panel explains its mosaic semantics, coverage limits, and separation from ECHO's quantitative measurements.

## Verification

- NASA GIBS `GetCapabilities` listed `NISAR_L2_Geocoded_Polarimetric_Covariance` and a time dimension. Its advertised daily intervals begin 2025-10-29 and extend through 2026-11-09 at retrieval time.
- A direct WMS `GetMap` request for 2026-10-20 over the Iraq NISAR sample area (WGS84 bounds 41.19, 36.69, 41.23, 36.73) returned HTTP 200, `image/png`, 267,976 bytes.
- Headless Firefox opened the live ECHO interface, exposed the three map-backdrop options, switched from MODIS to NISAR, and rendered the expected layer identifier, WGS84 bounds, PNG format, selected date, and source attribution in the DOM.
- The focused adversarial, investigation-renderer, and web suites passed: 59 tests.

## Scientific limits

ASF describes the Worldview/GIBS layer as mosaics of **PROVISIONAL** GCOV products, resampled to 15.625 m, with all acquisitions included and the best available product shown per area. Frequency, acquisition mode, and available polarization channels can vary across a mosaic; RGB rendering also differs between single- and dual-polarization products. It is not the selected scene's quantitative raster, a controlled before/after comparison, or an input to ECHO's analysis. Blank/transparent areas do not establish absence of SAR acquisitions. This backdrop never changes the provider QA disposition: the Iraq observation and candidate pair remain QA-held, and no change result is produced.

## Sources

- ASF, [Exploring NISAR Data in Worldview](https://nisar-docs.asf.alaska.edu/worldview/) — provisional mosaic semantics, date intervals, spatial resampling, and cross-product rendering limits.
- NASA, [GIBS Access Basics](https://nasa-gibs.github.io/gibs-api-docs/access-basics/) — public WMS/WMTS services and time dimensions.
- NASA, [GIBS Overview and acknowledgements](https://nasa-gibs.github.io/gibs-api-docs/) — pre-generated visualization tiles and requested attribution.
