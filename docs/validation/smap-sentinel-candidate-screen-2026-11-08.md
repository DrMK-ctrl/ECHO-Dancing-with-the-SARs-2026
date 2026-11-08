# SMAP/Sentinel-1 exact-AOI candidate screen validation

**Date:** 2026-11-08
**Disposition:** Retrieved and reproducible; quality-limited, excluded from interpretation.

## Scope and result

- Queried the NASA NSIDC SPL2SMAP_S V3 collection through CMR and requested bounded exact-AOI subsets through NASA Harmony for 2024-05-09 and 2024-06-02.
- The two returned granules share the same 1×1 EASE-Grid subset. The recorded projected cell polygon covers 100% of the requested AOI, while the AOI covers 11.86% of that 3002.69 m cell. The values therefore have coarse spatial support and are not interpreted as fine-scale measurements.
- The before cell is out of the product's stated numeric range and has nonzero retrieval and surface flags. The after cell is in range but also has nonzero retrieval and surface flags. There are zero paired cells meeting the declared eligibility rule.
- The record preserves both subset assets, SHA-256 hashes, CMR concepts, retrieval times, Harmony request parameters/history, grid identity, quality fields, and the area-intersection method.
- The product blends SMAP radiometry and Sentinel-1 backscatter. It cannot independently validate a Sentinel-1 result; ECHO uses none of its values in the causal interpretation. The H3 surface-driver explanation remains unresolved and not tested.

## Verification

- `tests/test_smap_screen.py` recomputes retained-subset quality and support metadata and compares it with the source record.
- The assessment builder verifies the source-record identity and subset hashes before linking the candidate as evidence that limits interpretation.
- The web evidence endpoint revalidates the linked record and both bounded asset checksums before returning source details.
- Full repository tests: **254 passed** at this validation checkpoint.
- `.venv/bin/python -m compileall -q echo tools/research` and `git diff --check` passed.

## Reproduction

See [Decision 0032](../decisions/0032-record-quality-limited-smaps1-candidate.md) for the authenticated retrieval command. The retained subsets and record are under `data/research/`; rebuilding the linked T163 assessment additionally requires the recorded SAR, DSWx-HLS, spatial-support, polarization, GPM, and SMAP/Sentinel-1 records.

## Limitations

This validates bounded retrieval, provenance, QA exclusion, geometry, and evidence linkage. It does not validate soil moisture, event causality, provider QA for the OPERA pair, or a temporal SAR change result. The SMAP/Sentinel overpass-time-difference field has conflicting units metadata; its raw value is retained but not used.
