# SMAP radiometer candidate spatial screen

The live NASA CMR search resolved one pinned SPL3SMP_E V006 collection and returned all 28 matching daily granules for 2024-05-07 through 2024-06-03. The 2024-05-08 and 2024-06-01 records coincide with the T163 SAR acquisition dates at daily-product date precision. The AOI is approximately 0.963 by 1.112 km; product grid posting is 9 km and published native radiometer footprint is approximately 36 km.

Disposition: `SCREENED_SPATIALLY_TOO_COARSE_FOR_AOI_SCALE_TEST`. This is not a provider QA failure. No product file or soil-moisture pixel was retrieved and quality flags were not evaluated. The metadata screen does not establish within-day observation-time alignment.

## Verification

- `.venv/bin/python -m pytest tests/test_smap_radiometer_candidate_screen.py tests/test_cross_sensor_investigation.py tests/test_web.py -q` — passed (42 tests), including the assessment relationship and linked-record validation.
- `.venv/bin/python -m compileall -q echo tools/research/screen_smap_radiometer_candidate.py tools/research/build_cross_sensor_investigation.py` — passed.
- `git diff --check` — passed.
- Headless Firefox UI path — passed: open the case's NASA optical-context inspector, open the matching evidence assessment, verify the SMAP card's dates and footprint, then open its linked evidence record and verify the CMR query and no-retrieval fields.
- [Investigation card screenshot](smap-radiometer-investigation-card-2026-11-08.png).
- Live CMR record: [`smap-radiometer-candidate-screen-T163-349925-2026-11-08.json`](../../data/research/smap-radiometer-candidate-screen-T163-349925-2026-11-08.json).
- Candidate-screen SHA-256: `c4bc571998ec955b23d31710eaf962a8eefd2aa6e8dd187dff2d91066ebadffb`.
- Product support: [NSIDC V006 user guide](https://nsidc.org/sites/default/files/documents/user-guide/spl3smp_e-v006-userguide.pdf) and [product page](https://nsidc.org/data/spl3smp_e/versions/6).

The assessment and UI link this record as `NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN`, show the catalog dates and scale mismatch, and assess it as `DOES_NOT_DISTINGUISH`. No soil-moisture map or causal claim is derived from this metadata-only screen.
