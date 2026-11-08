# Decision 0036: screen independent SMAP radiometer support before retrieval

Date: 2026-11-08

## Decision

Screen NASA NSIDC SMAP SPL3SMP_E V006 catalog coverage and published spatial support before downloading its daily HDF5 products for the T163 surface-state investigation. Retain the metadata record, link it to the assessment, and expose its scale disposition in the investigation view.

## Evidence and rationale

The CMR screen returned 28 consecutive daily granules from 2024-05-07 through 2024-06-03, including the two SAR dates, 2024-05-08 and 2024-06-01. The selected product is radiometer-only and does not use Sentinel-1 inputs. Its published 9 km grid posting and approximately 36 km native radiometer footprint are much coarser than the AOI (approximately 0.96 by 1.11 km). It cannot resolve within-AOI surface-state patterns corresponding to the SAR cells.

This is a spatial-suitability screen, not a quality rejection. No HDF5 granule was downloaded, no pixel value or provider quality flag was read, and no SMAP measurement entered the assessment. The retained record preserves the CMR query, response checksums, granule identifiers, daily dates, and explicit no-retrieval state.

## Investigation consequence

The candidate is linked to the alternative surface-state hypothesis as `DOES_NOT_DISTINGUISH`. It is not used as corroboration or a driver measurement. The independent-source follow-up remains open for observations whose spatial support and timing can address the AOI-scale question. This incremental screen advances the observation-to-assessment chain without making the broader investigation depend on this one source.

## Authoritative references

- [NSIDC SMAP Enhanced L3 Radiometer V006 user guide](https://nsidc.org/sites/default/files/documents/user-guide/spl3smp_e-v006-userguide.pdf)
- [NSIDC SPL3SMP_E V006 product page](https://nsidc.org/data/spl3smp_e/versions/6)
- [NASA CMR API documentation](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)

## Reproduction

```bash
.venv/bin/python tools/research/screen_smap_radiometer_candidate.py \
  --start-date 2024-05-07 --end-date 2024-06-03 \
  --bounds -51.24,-30.04,-51.23,-30.03 \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output data/research/smap-radiometer-candidate-screen-T163-349925-2026-11-08.json
```

This metadata-only search may return updated catalog metadata and response checksums when rerun.
