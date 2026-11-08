# Surface-state test-design validation — 2026-11-08

## Implemented behavior

The open T163 independent-surface-state search now carries a pre-search contract. It requires the analyst to select a single mechanism branch before retrieval and records the expected observation, what would weaken that branch, when the result must remain inconclusive, and the data acceptance gates. It explicitly lists the water-change and SAR product-quality hypotheses as not tested by this observation.

The status remains `NOT_SEARCHED`; no source candidate, measurement, finding, or ranking is implied by the protocol.

## Verification performed

- `.venv/bin/python -m pytest -q tests/test_investigation.py tests/test_cross_sensor_investigation.py` — 55 passed.
- `.venv/bin/python -m pytest -q` — 267 passed.
- Python bytecode compilation and `git diff --check` — passed.
- Firefox headless against the local application opened the T163 linked assessment and the pre-search design. It displayed all five acceptance gates, the selected H3 branch and its falsification/inconclusive conditions, and both hypotheses that the candidate cannot test.
- `GET /api/cross-sensor-assessment` returned the rebuilt unresolved assessment and F7 test design with all five gates.

## Limits

This records a test protocol for a future evidence search. It does not locate a suitable independent product, validate any surface-state measurement, compute spatial association, rank evidence requests, resolve H3, or clear RTC-S1 QA. Any retrieved candidate still requires product-specific scientific review.
