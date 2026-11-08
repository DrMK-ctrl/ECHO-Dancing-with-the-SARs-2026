# T024 SMAP L4 context interface validation — 2026-11-08

## Result

The active T024 investigation renders the NASA SMAP L4 model-context summary and opens its checksum-validated source record from a dedicated card.

## Browser path

Firefox headless loaded the local application at `/?case_id=rio-grande-do-sul-cross-sensor-diagnostic-2024`, opened **OPEN CASE INVESTIGATION**, and verified that the card displayed both analysis dates, the before/after model analysis, the descriptive difference, 9 km native grid scale, distance from the AOI center, and the unresolved interpretation limits. Selecting **INSPECT SMAP L4 SOURCE AND PROCESSING** opened the linked record in the source inspector. The record type was `ECHO_SMAP_L4_REGIONAL_SOIL_MOISTURE_CONTEXT_SCREEN`; its retained source path and SHA-256 were shown by the inspector.

Screenshot: [T024 SMAP L4 context card and source inspector](smap-l4-t024-interface-2026-11-08.png).

## Boundary

This confirms presentation and provenance navigation only. The displayed 0.003538 m³/m³ difference is model-derived context on a 9 km grid, not an AOI-scale soil-moisture measurement or significance test. The evidence remains `DOES_NOT_DISTINGUISH`; H3 remains unresolved and not testable with the retained evidence. The SAR comparison remains a diagnostic Sentinel-1-derived OPERA RTC-S1 product without consolidated provider QA.
