# Decision 0034: link inter-acquisition rainfall chronology

**Status:** accepted for the T163 diagnostic investigation
**Date:** 2026-11-08

## Decision

Retain the complete daily NASA GPM IMERG Final Daily V07 series between the two OPERA RTC-S1 acquisitions and link it to the investigation assessment as contextual evidence. The interval comprises 23 full UTC days, 9–31 May 2024. The nearest native cell has 48/48 valid half-hourly samples on every day. Its estimates sum to 214.93 mm, with a daily maximum of 77.44 mm/day on 23 May.

The rainfall series is regional context at approximately 0.1° native spacing. ECHO does not interpolate it to the SAR grid, treat it as AOI soil moisture, infer flooding from it, or attribute the SAR response to rainfall. H3 remains unresolved; this source is linked as `DOES_NOT_DISTINGUISH` and helps locate temporal context without being mistaken for a discriminating surface measurement.

## Evidence chain and interface

The derived chronology records hashes for the SAR pair and the two GPM source records, retains per-day granule identifiers and subset checksums, and is deterministically rebuilt from the daily records. The assessment builder revalidates the source lineage and values. The web layer checks linked record hashes, source identities, bounded day coverage, daily-series arithmetic, and chronology parent links. The investigation view now shows the inter-acquisition sequence and lets the analyst inspect its source record.

The linked daily GPM source record can contain up to 31 bounded UTC days. The web evidence reader validates that the number of retained source subsets matches the declared interval, while preserving the existing checksum and project-root checks.

## Reproduction

Retrieve missing daily subsets with `tools/research/retrieve_gpm_daily_context.py`, then build the chronology:

```sh
.venv/bin/python -m tools.research.build_gpm_interacquisition_context \
  --sar-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --intervening-gpm-record data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json \
  --trailing-gpm-record data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output data/research/gpm-imerg-interacquisition-T163-349925-2024-05-08-06-01.json
```

The case manifest links the daily source and derived chronology. NASA GPM provenance and product references are documented in [Decision 0029](0029-nasa-gpm-context-in-investigation.md).

## Scientific boundary

GPM's coarse grid does not resolve the SAR AOI and measures precipitation estimates, not soil moisture, surface water, or flood extent. The daily chronology supports asking when regional rainfall occurred and whether higher-resolution independent surface-state observations should be sought. It does not establish persistence, a causal mechanism, or a validated SAR change result. OPERA RTC-S1 remains Sentinel-1 diagnostic evidence with unresolved consolidated provider QA; it is not NISAR.
