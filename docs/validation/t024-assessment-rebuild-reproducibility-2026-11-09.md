# Reproducible rebuild of the active T024 assessment

Date: 2026-11-09

## Result

The active T024 assessment was rebuilt from its 18 retained source records, including the second-pair WTR-2 mask-sensitivity overlay. Supplying its retained timezone-aware `created_at_utc` produced byte-identical JSON.

- Assessment: [`opera-rtc-cross-sensor-investigation-T024-050661-2026-11-09-mask-sensitivity.json`](../../data/research/opera-rtc-cross-sensor-investigation-T024-050661-2026-11-09-mask-sensitivity.json)
- SHA-256: `46087923e0c74668c3029c9d26cb8ac19bdb5d05e86ff623e43a84d3e5c3901c`
- Evidence inputs: all 18 `relative_path` entries and checksums in the assessment's `evidence_artifacts` list
- Build method: `tools/research/build_cross_sensor_investigation.py` with the same source-to-argument mapping as the automated reproduction test
- Network access: none; the rebuild reads retained local records only

`tests/test_cross_sensor_investigation.py::test_retained_t024_assessment_rebuild_is_byte_reproducible` repeats this check and compares the rebuilt bytes with the retained assessment. The timestamp is fixed only to reproduce this exact version; a new assessment revision must use its actual build time.

## Scientific boundary

Reproducible serialization and source-linked calculations verify the software record, not the scientific correctness of analyst-authored relationships. The OPERA RTC-S1 pair remains diagnostic, the optical and other contextual products retain their recorded limits, and the physical explanation remains unresolved.
