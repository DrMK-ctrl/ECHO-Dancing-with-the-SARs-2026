# Arbitrary Hawaii AOI NISAR measurement preview — 2026-11-12

## Result

In Firefox, an analyst-drawn WGS84 rectangle in Hawaii was used for ASF discovery and a bounded read of an authentic NISAR L2 GCOV measurement. ECHO placed eligible measurement pixels on the selected geographic extent and exposed acquisition, product, measurement, provider QA, access, and pixel-quality details in the map inspector.

## Observation and measurement

- AOI (west, south, east, north): `-155.4988, 19.4007, -155.4888, 19.4102` (EPSG:4326), selected through the map after zooming in for screen-coordinate precision.
- Product: `NISAR_L2_PR_GCOV_033_072_D_079_4005_DHDH_A_20261017T045813_20261017T045833_P05023_N_P_J_001`.
- Acquisition: 2026-10-17 04:58:13–04:58:33 UTC; path 72, frame 79, descending, partial coverage, provisional maturity, HH/HV.
- Measurement: `/science/LSAR/GCOV/grids/frequencyA/HHHH`, linear gamma-zero power, displayed as `10 log10(γ⁰)`.
- Bounded read: 107 × 107 pixels in EPSG:32604; 10,997 pixel centers fell in the AOI and all 10,997 were display eligible. The read requested 9,221,206 range bytes rather than downloading the full product.
- Display stretch: −11.40 to −2.19 dB (2nd–98th percentile).
- Provider QA: **FAIL**, from a 1,441-byte ASF summary retrieved 2026-11-12. The inspector reported zero nonvalid-mask, exception, unfocused, unknown-exception, and nonfinite/nonpositive exclusions among the shown pixels.

The interface explicitly labeled this a QA-held diagnostic preview and stated “no change result.” Pixel-level display eligibility does not override the product-level QA failure.

## Browser evidence and map behavior

Firefox displayed the raster over the selected AOI with coordinate graticule, timeline, acquisition details, and QA inspector. The captured screen shows the selected area near 19.41°N, 155.49°W. NASA GIBS context was marked unavailable in that capture; ECHO did not mislabel the measurement raster as a basemap. The local geographic coordinate frame and georeferenced raster remained visible.

Screenshot: [`hawaii-arbitrary-live-nisar-gcov-preview-2026-11-12.png`](assets/hawaii-arbitrary-live-nisar-gcov-preview-2026-11-12.png)  
SHA-256: `c7a10b4ec562292c67d32fef202f384ef4951553a9aeda9aa87b2d23abd979b3`

## Interpretation and limits

This is a second geographically independent arbitrary-area browser demonstration of real NISAR measurement retrieval and map display, complementing the Iraq workflow. It establishes neither a temporal change nor an event, cause, or validated scientific result. The product remains provider-QA failed. No machine-readable JSON record for this specific Hawaii response was retained with this note; the screenshot and displayed run details are the retained evidence.

The screenshot's GIBS-unavailable state did not yield a confirmed application root cause. A fresh Firefox session showed the NASA context request for another region and a global view without setting the unavailable state, and rapid zooming did not reproduce an erroneous failure flag. A direct GIBS request returned an image response header, while a subsequent full-body request timed out, so service/rendering variability remains possible. This should be revisited if the backdrop failure recurs consistently for a fixed request.
