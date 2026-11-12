# Saved-draft adversarial challenge validation

**Date:** 2026-11-12

## Scope

Validated the locally saved assessed-draft challenge route and its map-first investigation UI integration. The source case for the API test is an explicitly QA-held pair. No satellite measurements were recalculated in this validation.

## Checks

- The local API returns a challenge dossier only for a valid, saved, assessed snapshot and one selected hypothesis. The returned snapshot SHA-256 matches the requested content-addressed draft ID.
- An unsaved/unassessed snapshot and an unknown hypothesis are rejected. The QA-held source status is preserved; measurement recalculation is false and sensitivity is `NOT_RECOMPUTED_FOR_DRAFT`.
- The deterministic dossier exposes analyst-recorded relationships as unauthenticated, source records without relationships as unassessed, and follow-ups targeting the selected hypothesis. It does not update the draft.
- The browser renderer presents no challenge action before snapshot save and presents the selected-hypothesis action after save. Source links open the draft's existing source inspector.
- Focused automated tests: `.venv/bin/pytest -q tests/test_investigation_draft.py tests/test_adversarial.py tests/test_web.py tests/test_investigation_renderer.py` — **113 passed**.
- Full automated suite: `.venv/bin/python -m pytest -q` — **480 passed**.

## Limitations

This feature reorganizes analyst-entered material; it does not independently decide whether a finding survives a scientific test. Draft measurement fields are inventoried, not validated or recomputed. Sensitivity tests, provider QA verification, source-independence assessment, and physical-cause adjudication remain unavailable in this draft path. The established case challenge workflow retains its existing checksum-linked scientific adapters and QA gates.
