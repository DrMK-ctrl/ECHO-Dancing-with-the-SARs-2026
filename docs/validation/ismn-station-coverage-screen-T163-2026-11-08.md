# ISMN station-coverage screen — T163

**Date:** 2026-11-08

**Result:** No inventoried station has useful proximity and time coverage for both SAR dates.

## Method

Fetched the public ISMN station metadata inventory and filtered its 3,347 station coordinates by great-circle distance from the T163 AOI center (`-30.035, -51.235`). The source response was HTTP 200; its retrieval time, ETag, byte count, and SHA-256 are retained in the structured record. No station observation archive was downloaded.

The inventory lists no stations within 100 km. Its nearest station is COSMOS `Santa Maria UFSM`, about 245.88 km away, with listed soil-moisture coverage only from 2014-06-04 through 2014-07-23. This is neither spatially close to the approximately 1 km AOI nor temporally overlapping the 2024-05-08/09 and 2024-06-01/02 SAR acquisitions.

See the [structured screen and source metadata](../../data/research/ismn-station-coverage-screen-T163-2026-11-08.json). ISMN describes the inventory and its measured variables on its [data availability page](https://ismn.earth/data/data-availability/); the [data portal](https://ismn.earth/data/data-view/) says registration is required for observation downloads. Since no candidate passed the inventory screen, no registration or download was needed for this check.

## Disposition

This closes the ISMN route for the selected AOI and dates only. It does not prove that no suitable field measurements exist in other networks or archives. The soil-moisture branch remains untested; no scientific or SAR QA disposition changes.
