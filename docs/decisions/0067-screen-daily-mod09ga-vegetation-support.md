# Screen daily MOD09GA vegetation support for T163

**Date:** 2026-11-08

## Context

T163's vegetation hypothesis lacked a daily NASA optical screen aligned to both SAR acquisition dates. MOD13Q1 is a 16-day composite and has no accepted paired land support for this AOI. The NASA Terra/MODIS MOD09GA product offers daily 500 m reflectance, but its state QA has 1 km support and must be considered before interpreting vegetation indices.

## Decision

Retrieve exact-date MOD09GA bounded subsets for the T163 AOI and preserve provider and retrieval-service identity separately: NASA LP DAAC CMR collection metadata, with NASA LAADS DAAC OPeNDAP subset retrieval. Apply MOD09GA's documented `QC_500m` and `state_1km` flags on common native 500 m centers. Require clear, shadow-free, cloud-free land-class support on both dates before computing a vegetation index difference.

The actual pair supplies six common 500 m centers. Their reflectance-band quality fields are best category, but the associated 1 km state QA classifies all as shoreline or shallow inland water, and the earlier observation also has cloud/shadow flags. No paired NDVI or SAR association is calculated. Link the record only as interpretation-limiting evidence to H4 and retain the vegetation follow-up as `RETRIEVED_QUALITY_LIMITED`.

## Verification and consequences

The bounded screen record retains both granule identifiers, CMR concept IDs, acquisition dates, source links, the source-pair checksum, all selected native pixel values and QA fields, and checksums for each subset response. It remains NASA optical context, not SAR validation. The active causal disposition and provider QA status of the Sentinel-1 pair remain unchanged.

See the [MOD09GA validation record](../validation/mod09ga-vegetation-screen-T163-2026-11-08.md) and [structured source record](../../data/research/mod09ga-vegetation-candidate-T163-349925-2026-11-08.json).
