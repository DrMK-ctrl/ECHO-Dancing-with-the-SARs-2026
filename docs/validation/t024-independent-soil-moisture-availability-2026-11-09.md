# T024 independent soil-moisture source availability — 2026-11-09

## Result

The active T024 assessment now links two reproducible source-availability screens to the H3 independent soil-moisture follow-up. Neither source produced soil-moisture measurements for the case, and neither changes H3 from `UNRESOLVED` / `NOT_TESTABLE_WITH_RETAINED_EVIDENCE`.

## NASA ECOSTRESS catalog screen

NASA CMR collection `ECO_L3G_SM`, version `002`, was queried for the declared T024 AOI (`[-51.24, -30.04, -51.23, -30.03]`), a regional bounding box (`[-52, -31, -50, -29]`), and globally. The two AOI and regional windows were 2024-04-20 through 2024-05-20 and 2024-05-15 through 2024-06-15; the global target window was 2024-04-01 through 2024-07-01. These five target queries returned zero granules. The global March 1–31 positive control returned 377 hits across four retained pages, confirming that the selected collection/version was discoverable outside the target interval.

Every response body, reported hit count, query URL, page number, byte count, and SHA-256 is retained under [`data/research/source-artifacts/soil-moisture-T024-050661-2026-11-09/`](../../data/research/source-artifacts/soil-moisture-T024-050661-2026-11-09/). The product's nominal 70 m soil-moisture layer is model-derived, not a direct 70 m soil-moisture measurement. No product pixels were retrieved or evaluated.

## ISMN station inventory

The public [ISMN station inventory](https://ismn.earth/static/dataviewer/network_station_details.json) response is retained with its retrieval metadata, byte count, and SHA-256. The snapshot contained 89 networks and 3,347 stations. No station was within 100 km of the T024 AOI center. The nearest inventory station was COSMOS station 2850 (Santa Maria UFSM), 245.88 km away; its inventory-listed series dates were 2014-06-04 to 2014-07-23, outside the May/June 2024 SAR acquisitions. No ISMN measurement archive was downloaded.

This result is limited to the retained public inventory snapshot. It does not establish that no suitable station or alternative archive exists elsewhere. A station is also a point measurement whose representativeness would require separate evaluation even if geographically closer.

## Assessment linkage and reproduction

Run the catalog and station screens from the repository root:

```bash
./.venv/bin/python tools/research/screen_t024_soil_moisture_sources.py
```

Rebuild the T024 assessment using the commands in [the HLS coverage-cutoff validation](t024-hls-cutoff-sensitivity-2026-11-09.md), append these arguments, and replace that command's existing `--output` argument:

```bash
  --ecostress-sm-screen-record data/research/ecostress-soil-moisture-catalog-screen-T024-050661-2026-11-09.json \
  --ismn-station-screen-record data/research/ismn-station-coverage-screen-T024-050661-2026-11-09.json \
  --hls-candidate-screen-record data/research/hls-l30-vegetation-T024-050661-2026-11-09-jun09.json \
  --output data/research/opera-rtc-cross-sensor-investigation-T024-050661-2026-11-09-soil-moisture-screen.json
```

The case manifest selects this assessment. Both the builder and web validator re-read the linked CMR pages and ISMN inventory, verify checksums and byte counts, recompute catalog pagination and station coverage, and keep the findings as availability metadata. A regression test confirms the screens remain linkable without a GPM record; another rejects a changed inventory summary. This workflow does not test H3 or resolve the diagnostic status of the Sentinel-1-derived OPERA RTC-S1 pair.
