# Reproducible T163 assessment refresh

Date: 2026-11-09

## Result

The active T163 investigation assessment has been rebuilt from its documented retained source records with the current builder. The prior `hls-cutoff-sensitivity` assessment remains intact. The case manifest now selects `opera-rtc-cross-sensor-investigation-T163-349925-2026-11-09-source-refresh.json`.

The rebuild added detail from the retained MOD09GA state-QA pixels (`land_water_class_codes` `[2, 3]`, `cloud_state_codes` `[0, 2]`) and linked the available SMAP, ECOSTRESS, and ISMN screens to the open soil-moisture evidence search. Its narrative continues to describe those records as screens/context. No source was promoted to directional evidence. All six hypothesis dispositions and the overall `CAUSAL_INTERPRETATION_UNRESOLVED` status match the prior assessment.

## Reproducibility

The command in [the end-to-end workflow record](end-to-end-investigation-workflow-2026-11-08.md) now passes the active assessment's retained `created_at_utc` through `--created-at-utc`. Re-running that documented command with the same source records produced byte-for-byte identical JSON. SHA-256: `9a6a3e4750fac5141614dc0c83ecc53a0199a35b4f8c615ae0fa5f0b7987607c`.

`echo.web._validate_assessment_record` accepted the active assessment and resolved all 24 linked evidence records. The full software suite passed: `PYTHONPATH=. .venv/bin/python -m pytest -q --tb=short` — **413 passed**. The focused timestamp test verifies repeated builds with an explicit timezone-aware timestamp are identical and a naive timestamp is rejected.

## Limits

This rebuild used retained local source records and processing assets; it made no provider request and added no satellite measurement. MOD09GA remains `RETRIEVED_QUALITY_LIMITED`, the OPERA RTC-S1 pair remains diagnostic without a consolidated provider QA verdict, all causal explanations remain unresolved or not tested, and the result is not a validated flood interpretation. The timestamp override supports reproducible serialization; it does not make a historical timestamp appropriate for a newly created assessment.
