# Link the GPM IMERG inter-acquisition chronology to T024

**Status:** Accepted
**Date:** 2026-11-08

## Context

The T024 OPERA RTC-S1 comparison spans 2024-05-11 to 2024-06-04. ECHO already retained nearby seven-day GPM IMERG context, but the 23 complete UTC days between the SAR acquisitions had not been represented as a continuous chronology in this case's active investigation assessment. The T024 AOI is smaller than one native GPM grid cell, so the nearest-cell daily series is regional context rather than an AOI-resolved hydrologic measurement.

## Decision

Link the checksummed NASA GPM IMERG Final Daily V07 chronology to the T024 water-change hypothesis as `DOES_NOT_DISTINGUISH`. Preserve provider, mission, product, acquisition interval, native-cell location, daily sample completeness, retrieval provenance, and links to the bounded source subsets. The assessment builder and evidence loader must reject any attempt to present this chronology as supporting or resolving the water hypothesis.

The T024 case manifest now selects the new versioned assessment record. The previous assessment remains retained. The source subsets are bounded spatial/temporal extracts (30 files, about 1.2 MB total), not full granules.

## Consequences and limits

All 23 inter-acquisition days have 48/48 nominal half-hourly samples at the nearest approximately 0.1-degree cell. The daily mean precipitation-rate estimates sum to 181.385 mm; the maximum is 77.44 mm/day on 2024-05-23. These values establish only a regional precipitation chronology at that grid cell. They do not establish local rainfall distribution, runoff, AOI surface-water extent, soil moisture, or the cause of the SAR response. The RTC-S1 products retain their diagnostic status and unresolved provider-QA limitation.

NASA source: [GPM IMERG Final Daily V07 at NASA GES DISC](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary?keywords=imerg), DOI `10.5067/GPM/IMERGDF/DAY/07`.
