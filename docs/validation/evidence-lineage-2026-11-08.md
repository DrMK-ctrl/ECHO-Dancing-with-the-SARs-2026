# Evidence-lineage verification — 2026-11-08

## Implemented behavior

The T163 assessment now carries explicit `derived_from_evidence_ids` and `shares_source_observations_with` links for its retained evidence artifacts. The web endpoint validates identifiers and derivation cycles before serving the assessment. The investigation inspector presents all nine records in a collapsed dependency panel.

## Verification performed

- `PYTHONPATH=. .venv/bin/pytest -q` — **249 passed**.
- `git diff --check` — passed.
- `.venv/bin/python -m compileall -q echo tools/research/build_cross_sensor_investigation.py` — passed.
- Firefox headless, through the running local ECHO server — opened NASA optical context, opened the linked assessment, expanded the dependency panel, and confirmed nine artifact rows. The browser check found both the VH-to-VV shared-acquisition relation and the spatial-overlay derivation relation in rendered text.
- `GET /api/cross-sensor-assessment` — returned the regenerated nine-artifact record with `CAUSAL_INTERPRETATION_UNRESOLVED`; the physical explanation and provider-QA status were not promoted.

## Limits

These links document known computation and shared acquisition relationships. They do not quantify statistical dependence or establish that records without a link are independent. This is a provenance aid, not an automated evidence-weighting or causal-inference model.
