# Screen NASA SMAP L4 as regional model context for T024

**Date:** 2026-11-08
**Status:** Accepted

## Context

T024's open soil-moisture follow-up needed a source screen that would not mistake coarse model output for an independent observation. NASA NSIDC SPL4SMAU Version 8 provides 3-hourly soil-moisture analyses on a 9 km EASE-Grid. NSIDC describes these as land-surface-model output informed by assimilated SMAP brightness temperatures. For this location, the product's Version 8 guide also documents IMERG Final V07 precipitation forcing. These properties make it potentially useful regional context, but not an independent AOI-scale soil-moisture measurement alongside ECHO's GPM chronology.

## Decision

Screen the nearest SPL4SMAU analysis update to each T024 SAR acquisition through NASA CMR and Harmony. Retain the bounded native-grid NetCDF subsets, granule and collection identities, acquisition offsets, Harmony history, coordinate grid, checksums, analysis values, ensemble spreads, and assimilated brightness-temperature availability. Re-read the retained subsets when building the investigation assessment.

Classify this route as `SCREENED_REGIONAL_MODEL_CONTEXT_NOT_SUITABLE_FOR_AOI_SCALE_DISCRIMINATION` for T024. Link it to the soil-moisture hypothesis as `DOES_NOT_DISTINGUISH`, keep H3 unresolved and not testable, and leave the independent-soil-moisture search open. Preserve the potential IMERG input overlap explicitly. Do not interpret ensemble spread as QA status or as a significance threshold.

## T024 screen result

- CMR selected the 09:00 UTC SPL4SMAU updates, 10.22 and 10.23 minutes from the 2024-05-11 and 2024-06-04 SAR acquisitions.
- The nearest native grid center is approximately 2.70 km from the AOI center; its posted cell is 9 km across while the AOI is about 1 km.
- The model analysis changes from 0.385752 to 0.389290 m³/m³ at that cell, a difference of 0.003538 m³/m³. The corresponding ensemble standard deviations are 0.013692 and 0.018409 m³/m³. No covariance model was used, so this is descriptive context, not a significance test.
- Both horizontal and vertical assimilated brightness-temperature and observation-time fields are fill values across the six retrieved grid cells at both selected analysis times.
- The two source subsets are each about 80 KiB and are checksum-linked in the retained screen record.

The product remains model-derived; the absent local brightness-temperature fields do not establish that the product used no SMAP observations elsewhere or at other times. This screen neither validates the diagnostic OPERA RTC-S1 pair nor identifies flood extent or cause.

## Consequences

The T024 assessment now exposes the source record through the existing evidence inspector and identifies its role and limitations. The previous assessment remains retained; the case manifest selects the new assessment. CMR selection, subset-size bounds, native-grid identity, checksums, time alignment, and recomputed summaries are validated. NASA documentation is linked from the source record:

- [SPL4SMGP Version 8 product page](https://nsidc.org/data/spl4smgp/versions/8)
- [SPL4SMAU/SMGP Version 8 user guide](https://nsidc.org/sites/default/files/documents/user-guide/multi_spl4smau-v008-userguide.pdf)
