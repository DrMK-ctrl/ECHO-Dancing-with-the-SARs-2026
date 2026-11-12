# Live arbitrary-AOI NISAR map preview — 2026-11-12

## Result

Firefox completed the live ECHO workflow from a newly drawn WGS84 AOI to an authentic NISAR GCOV measurement rendered on the geographic map. The layer remains explicitly diagnostic because the source product's ASF provider QA is `FAIL`.

## Reproduction context

- Local application: writable ECHO UI served on loopback with the Iraq NISAR catalog case.
- AOI drawn in the map: west `41.205`, south `36.705`, east `41.215`, north `36.715` (EPSG:4326). This is a smaller area inside the registered Iraq case bounds, drawn during the browser session.
- Selected observation: `NISAR_L2_PR_GCOV_033_122_D_070_2005_DHDH_A_20261020T160723_20261020T160758_P05023_N_F_J_001`.
- Provider/product: Alaska Satellite Facility DAAC / NASA NISAR L2 GCOV; acquisition `2026-10-20T16:07:23Z` to `16:07:58Z`; path 122, frame 70, descending, provisional, HH/HV.
- Measurement: `/science/LSAR/GCOV/grids/frequencyA/HHHH`, linear gamma-zero backscatter. ECHO converted the display colors to `10 log10(γ⁰)` and positioned the raster using the source grid's WGS84 pixel corners.
- Bounded window: 46 × 56 pixels in EPSG:32637; 2,476 pixel centers selected and displayed for the AOI.
- Live provider QA response: `FAIL`, 1,441-byte QA summary. The interface showed `QA-HELD REAL SAR PREVIEW`, the QA failure, and “no change result.” No temporal measurement or event interpretation was produced.

The map, AOI outline, backscatter raster, acquisition timeline, paired-observation QA hold, and source inspector were visible together in Firefox. Screenshot: [`iraq-arbitrary-live-nisar-gcov-preview-2026-11-12.png`](assets/iraq-arbitrary-live-nisar-gcov-preview-2026-11-12.png), SHA-256 `2f15bf7680a22cd355e74938e87a160042eca1bf58eaecf1352943a7d29bb8ca`.

## Interpretation boundary

This demonstrates that a user-drawn sub-area can flow through the existing observation selection, bounded authenticated NISAR read, geospatial placement, quantitative display, and provenance/QA inspector. The pixels are genuine provider measurements, but the provider QA failure prevents treating this as a scientifically accepted analytical result. The preview is one acquisition; it does not establish temporal change, an event, or a physical cause. The earlier retained full-Iraq preview record is separately checksummed at [`nisar-iraq-p05023-hhhh-preview-2026-11-08.json`](../../data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json); it is not the response record for this newly drawn sub-AOI.

## Verification limits

This was a real Firefox run against the authenticated ASF data service. It validates one newly drawn AOI in Iraq. It does not show that every geographic region or product has valid display pixels, nor that the Iraq pair passes QA or supports change analysis. The Sakurajima test still returned no display-eligible pixels, while Hawaii was validated for catalog discovery only.
