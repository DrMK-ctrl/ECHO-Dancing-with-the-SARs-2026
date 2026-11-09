# Live CMR and LAADS MOD09GA rerun

Date: 2026-11-09

Case: T163-349925, Rio Grande do Sul, southern Brazil

Disposition: live data access verified; vegetation screen remains quality-limited

## Access result

The earlier full-screen attempt stopped while the local client was opening its CMR connection. Rechecking through the same local Earthdata configuration succeeded: a direct CMR request returned HTTP 200, and the complete screen then selected the same two Terra/MODIS MOD09GA Collection 6.1 granules and retrieved all 20 bounded LAADS OPeNDAP subsets. Every subset response returned HTTP 200. Earthdata credentials remained local; no authorization change or credential transfer was needed.

The rerun record is retained separately at [`mod09ga-vegetation-recheck-T163-349925-2026-11-09.json`](../../data/research/mod09ga-vegetation-recheck-T163-349925-2026-11-09.json). It records 277,871 bytes across 20 subsets, keeps CMR granule identity separate from LAADS retrieval provenance, and links to the current T163 pair SHA-256 `41e040338b4726766a8e1724e74bac2f211cd71a07190f66711b04a4843603cf`.

## Reproducibility comparison

The rerun was compared with the retained 2026-11-08 screen. Both runs selected:

- Before: `MOD09GA.A2024129.h13v12.061.2024131043655`
- After: `MOD09GA.A2024153.h13v12.061.2024155024914`

The two records have identical observation summaries, bounded pixel records, and all 20 subset-response tuples `(granule_id, constraint, HTTP status, byte count, SHA-256)`. Both retain six common 500 m pixel centers and zero pixels passing the strict paired land-and-QA gate. Therefore neither computes paired NDVI change. The run reproduces the same quality-limited result; it adds no new vegetation finding and does not validate the diagnostic SAR measurement.

To reproduce the retrieval from the repository root:

```bash
.venv/bin/python tools/research/screen_mod09ga_vegetation.py \
  --pair-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output data/research/mod09ga-vegetation-recheck-T163-349925-2026-11-09.json
```

The source pair and both vegetation screens preserve the provider QA distinction: MODIS supplies optical context only; it does not establish or validate a SAR-derived water boundary.

Checksums:

- 2026-11-08 retained screen: `81ffea46316d2d0dc66fb11a2796c91c8d1b2a051ff5dd4e7581544a450ca8d0`
- 2026-11-09 rerun: `33fb4bc3158f625571dff5ed8335e8cc8d9a4b2460c85976c9391f715aed1234`
