# T024 HLS coverage-cutoff sensitivity — 2026-11-09

The active T024 assessment now carries the complete native-grid HLS L30/SAR association sensitivity series from its linked source record:

| Minimum common clear-land optical area | SAR cells | Descriptive Pearson r (NDVI change vs. SAR log-ratio) |
|---:|---:|---:|
| 25% | 312 | −0.2499 |
| 50% | 265 | −0.2745 |
| 75% | 218 | −0.2717 |

These are descriptive associations over progressively smaller, nested supports. The r values are similar across these selected cutoffs; this is not a statistical robustness test. Neighboring cells are spatially dependent, no inferential statistics are computed, only 23.0% of AOI HLS centers are common clear land, and the underlying Sentinel-1/OPERA product pair remains diagnostic without a consolidated provider QA verdict. H4 remains `UNRESOLVED` and `DOES_NOT_DISTINGUISH`.

The assessment builder recomputes the association from the exact retained SAR/HLS records and checksummed bounded pixel subsets. It rejects altered derived rows. The application checks that the schema-3 cutoff rows and selected 75% summary match the linked association artifact. The map card displays the support count and r at each cutoff and retains links to inspect both source and derived records.

The T024 manifest selects `data/research/opera-rtc-cross-sensor-investigation-2026-11-09-temporal-series-gpm-smap-hls-l30-sensitivity.json`; the previous assessment snapshot remains retained.

Rebuild the assessment with the retained records:

```bash
.venv/bin/python tools/research/build_cross_sensor_investigation.py \
  --sar-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json \
  --optical-record data/research/dswx-hls-rtc-aoi-context-2026-11-07.json \
  --nearer-optical-record data/research/dswx-hls-nearer-rtc-context-2026-11-07.json \
  --catalog-screen-record data/research/dswx-hls-followup-screen-2026-11-07.json \
  --acquisition-conditions-record data/research/opera-rtc-acquisition-conditions-T024-050661-2026-11-08.json \
  --sar-temporal-series-record data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json \
  --gpm-before-record data/research/gpm-imerg-context-T024-050661-before-2024-05-11.json \
  --gpm-after-record data/research/gpm-imerg-context-T024-050661-before-2024-06-04.json \
  --gpm-intervening-record data/research/gpm-imerg-intervening-T024-050661-2024-05-12-05-27.json \
  --gpm-interacquisition-record data/research/gpm-imerg-interacquisition-T024-050661-2024-05-11-06-04.json \
  --smap-l4-context-record data/research/smap-l4-regional-context-T024-050661-2026-11-08.json \
  --hls-vegetation-record data/research/hls-l30-vegetation-T024-050661-2026-11-09.json \
  --hls-association-record data/research/hls-l30-ndvi-sar-association-T024-050661-2026-11-09.json \
  --output data/research/opera-rtc-cross-sensor-investigation-2026-11-09-temporal-series-gpm-smap-hls-l30-sensitivity.json
```

Verification:

- Full test suite: `.venv/bin/python -m pytest -q` — 388 passed.
- Association tampering check: changing one retained r value is rejected because the derived record no longer reproduces from linked observations.
- Live Firefox validation on the local application: the T024 assessment card rendered the 25%, 50%, and 75% cutoffs, counts (312/265/218), and correlations (−0.250/−0.275/−0.272); the card retained the diagnostic and nondiscriminating interpretation boundary.
