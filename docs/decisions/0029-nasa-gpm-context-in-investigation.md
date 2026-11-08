# Decision 0029: use bounded GPM precipitation as contextual evidence

**Status:** accepted for the Rio Grande do Sul diagnostic investigation
**Date:** 2026-11-08

## Decision

Use NASA GPM IMERG Final Daily (V07) as a contextual check for regional precipitation before each retained OPERA RTC-S1 acquisition. Retrieve one UTC day at a time through NASA Harmony, bounded to the case neighborhood. Retain the daily `precipitation` estimate and `precipitation_cnt` sample count with the returned NetCDF subsets and checksums.

The selected SAR AOI is much smaller than the product's 0.1° grid. ECHO therefore reports the nearest native cell and regional grid unchanged; it does not resample precipitation onto SAR pixels. A complete sample count indicates 48 valid half-hourly inputs for that daily estimate, not ground validation or certainty in the estimated precipitation.

## Observation and interpretation

The nearest native grid cell centered at approximately 51.25°W, 30.05°S has complete 48/48 half-hourly sampling on all 14 requested days. The daily estimates sum to 219.9 mm for 1–7 May 2024 and 14.3 mm for 25–31 May 2024. The windows end before the 8 May and 1 June SAR acquisition dates, respectively.

This is meaningful evidence that the two SAR acquisitions followed different regional precipitation conditions. It does not measure soil moisture, establish the state of water within the SAR AOI, identify the physical cause of the backscatter response, validate a flood boundary, or clear the RTC-S1 provider QA hold. ECHO links both records to H3 as `DOES_NOT_DISTINGUISH`; that hypothesis remains `UNRESOLVED` and `NOT_TESTED` for lack of scale-appropriate surface-driver measurements. The next evidence action is an availability-and-resolution screen for independent soil-moisture, vegetation, or in-situ observations that could resolve the AOI and bracket the acquisition dates.

## Reproduction and provenance

Run `tools/research/retrieve_gpm_daily_context.py` with the recorded case bounds, acquisition-relative date windows, and local Earthdata `.netrc` authentication. The script makes one small Harmony subset request per UTC day and records the exact NASA collection, granule IDs, native coordinates, variables, units, retrieval time, byte counts, and SHA-256 checksums. The retained subsets are under `data/research/source-artifacts/gpm-imerg-T163-349925-*`; no global daily files are downloaded.

Rebuild the linked assessment with `tools/research/build_cross_sensor_investigation.py` using the two GPM records and the retained SAR, DSWx-HLS, spatial-support, and polarization records. The assessment builder checks that each seven-day window precedes its corresponding SAR acquisition and verifies every bounded source-subset checksum. The application repeats those checksum checks when loading the linked assessment and exposes the daily records through its evidence inspector.

## References

- [NASA GES DISC: GPM_3IMERGDF V07](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary)
- [NASA GPM IMERG V07 technical documentation](https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation)
- [NASA Harmony API documentation](https://harmony.earthdata.nasa.gov/docs)
- Dataset DOI: `10.5067/GPM/IMERGDF/DAY/07`
