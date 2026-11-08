# T024 GPM IMERG chronology integration — 2026-11-08

## Result

The active T024 case assessment now links a complete NASA GPM IMERG Final Daily V07 precipitation chronology covering the 23 full UTC days between OPERA RTC-S1 acquisitions on 2024-05-11 and 2024-06-04. The nearest native cell is centered at `[-51.25, -30.05]`, approximately 0.1 degrees from the small SAR AOI. Each daily estimate has 48 of 48 nominal half-hourly samples; the nearest-cell total is 181.385 mm, with a peak of 77.44 mm/day on 2024-05-23.

The chronology is linked to the water-change hypothesis as `DOES_NOT_DISTINGUISH`. It is regional precipitation context, not a surface-water-extent or soil-moisture measurement. The hypothesis and case disposition remain unresolved; the SAR pair remains diagnostic because there is no consolidated provider QA verdict.

## Provenance and reproduction

- Provider/product: NASA GES DISC, GPM IMERG Final Daily V07, DOI `10.5067/GPM/IMERGDF/DAY/07`.
- Bounded daily source subsets: `data/research/source-artifacts/gpm-imerg-T024-050661-*`; each record stores source granule ID, retrieval reference, byte count, and SHA-256.
- Context records: `data/research/gpm-imerg-context-T024-050661-before-2024-05-11.json`, `data/research/gpm-imerg-intervening-T024-050661-2024-05-12-05-27.json`, `data/research/gpm-imerg-context-T024-050661-before-2024-06-04.json`.
- Derived chronology: `data/research/gpm-imerg-interacquisition-T024-050661-2024-05-11-06-04.json`; it links and revalidates the SAR-pair and GPM-context record checksums.
- Active assessment: `data/research/opera-rtc-cross-sensor-investigation-2026-11-08-temporal-series-gpm.json`; the T024 case manifest selects this version while retaining the earlier assessment file.

To rebuild the assessment, run:

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
  --output data/research/opera-rtc-cross-sensor-investigation-2026-11-08-temporal-series-gpm.json
```

To rebuild the inter-acquisition chronology from its bounded daily records:

```bash
.venv/bin/python tools/research/build_gpm_interacquisition_context.py \
  --sar-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json \
  --intervening-gpm-record data/research/gpm-imerg-intervening-T024-050661-2024-05-12-05-27.json \
  --trailing-gpm-record data/research/gpm-imerg-context-T024-050661-before-2024-06-04.json \
  --case-id rio-grande-do-sul-cross-sensor-diagnostic-2024 \
  --output data/research/gpm-imerg-interacquisition-T024-050661-2024-05-11-06-04.json
```

## Validation

The assessment builder verifies source record identities, checksums, GPM daily completeness, chronology sums, and the water-hypothesis relationship. The case API resolves the linked GPM record and checks its bytes against the assessment's recorded SHA-256. Regression tests cover the unresolved relationship and reject promoting the chronology to `SUPPORTS`.

- `.venv/bin/python -m pytest -q` — **342 passed**.
- `.venv/bin/python -m compileall -q echo tools/research` — passed.
- `git diff --check` — passed.

## Browser runtime check

Firefox headless 158.0.1 opened the local investigation workspace at `/?case_id=rio-grande-do-sul-cross-sensor-diagnostic-2024`. The T024 assessment rendered the 23-day rainfall card, displayed the 181.4 mm rounded total and the 77.44 mm/day peak on 2024-05-23, and showed its regional-context limitation. Clicking **INSPECT INTER-ACQUISITION CHRONOLOGY** opened the linked GPM JSON record; its record type and 23 complete daily samples were read from the rendered source inspector.

To repeat manually, start the local interface with `.venv/bin/echo serve --case-file data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json`, open `http://127.0.0.1:8000/?case_id=rio-grande-do-sul-cross-sensor-diagnostic-2024`, open **OPEN CASE INVESTIGATION**, then inspect the inter-acquisition chronology. This verifies browser rendering and source navigation, not a new visual-design acceptance review.

The event meaning is not validated by this integration. GPM's coarse spatial support, the lack of a direct water-extent measurement, and unresolved RTC-S1 provider QA remain material limitations.
