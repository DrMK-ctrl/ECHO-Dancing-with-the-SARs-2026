# T163 investigation workflow integration check

**Result:** Retained diagnostic case rebuilt reproducibly and accepted by the application's source-linked assessment validator.

## What was exercised

The T163 assessment builder consumed the retained OPERA RTC-S1 pair, NASA OPERA DSWx-HLS context, exact-grid overlays, polarization sensitivity, rainfall chronology, soil-moisture and vegetation screens, ANA narrative context, and acquisition-condition review. It produced an assessment with 20 evidence artifacts, six hypotheses, and ten follow-up actions. `echo.web._validate_assessment_record` accepted the generated assessment against the repository evidence root and resolved all 20 linked records.

The rebuilt record matched the retained assessment in all fields except `created_at_utc`. It preserves the diagnostic Sentinel-1/OPERA measurement status, the absence of a consolidated provider QA disposition, and the overall `CAUSAL_INTERPRETATION_UNRESOLVED` result. The optical-class-count hypothesis is `SUPPORTED_WITHIN_SCOPE` as a descriptive observation; water, soil-moisture, vegetation, acquisition-condition, and product-quality explanations remain unresolved or not tested. Follow-up actions retain separate quality-prerequisite, new-evidence-search, and reviewed-result tracks.

## Reproduction

From the repository root, build to a temporary path:

```bash
.venv/bin/python tools/research/build_cross_sensor_investigation.py \
  --sar-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical-record data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --catalog-screen-record data/research/dswx-hls-screen-T163-349925-2026-11-07.json \
  --spatial-support-record data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-2026-11-08.json \
  --polarization-vh-pair-record data/research/opera-rtc-live-pair-T163-349925-IW2-VH-2024-11-08.json \
  --polarization-vh-spatial-support-record data/research/opera-rtc-dswx-spatial-support-T163-349925-VH-2026-11-08.json \
  --polarization-sensitivity-record data/research/opera-rtc-polarization-sensitivity-T163-349925-2026-11-08.json \
  --acquisition-conditions-record data/research/opera-rtc-acquisition-conditions-T163-349925-2026-11-08.json \
  --gpm-before-record data/research/gpm-imerg-context-T163-349925-before-2024-05-08.json \
  --gpm-after-record data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json \
  --gpm-intervening-record data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json \
  --gpm-interacquisition-record data/research/gpm-imerg-interacquisition-T163-349925-2024-05-08-06-01.json \
  --smap-screen-record data/research/smap-sentinel-soil-moisture-screen-T163-349925-2026-11-08.json \
  --smap-radiometer-screen-record data/research/smap-radiometer-candidate-screen-T163-349925-2026-11-08.json \
  --hls-vegetation-record data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json \
  --hls-association-record data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json \
  --hls-s30-vegetation-record data/research/hls-s30-vegetation-screen-T163-349925-2026-11-08.json \
  --hls-s30-association-record data/research/hls-s30-rtc-ndvi-association-T163-349925-2026-11-08.json \
  --mod13q1-screen-record data/research/mod13q1-vegetation-candidate-T163-349925-2026-11-08.json \
  --guaiba-context-record data/research/ana-guaiba-official-flood-stage-context-2026-11-08.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output /tmp/echo-t163-investigation.json
```

Then load the JSON record and call `echo.web._validate_assessment_record(record, Path.cwd())`. The full software suite passed with `.venv/bin/python -m pytest -q` (**298 passed**). A standalone `pytest -q` invocation failed collection because that entry point omitted the repository root from the import path; it was not used for the passing result.

## Limits

This is a real-data workflow integration check, but the SAR source is Sentinel-1 RTC-S1 through OPERA, not NISAR. The pair remains diagnostic, not provider-QA-cleared. The assessment validator verifies provenance links, contract structure, and consistency; it does not verify the truth of analyst-assigned evidence relationships, causal explanations, or scientific suitability. The retained case and hypothesis assessments remain analyst-authored. No generalized automated Investigation Engine or new causal finding is demonstrated.
