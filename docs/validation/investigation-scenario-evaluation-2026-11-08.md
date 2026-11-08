# Controlled investigation scenario evaluation

**Result:** Integrated synthetic ambiguity scenario passed the investigation contract and browser-rendering checks.

## Scenario boundary

The fixture at `tests/fixtures/investigation-scenario-ambiguous-synthetic.json` is labeled `SYNTHETIC_TEST_ONLY_NOT_SATELLITE_EVIDENCE`. Its before/after values and difference are arbitrary test quantities. They are not radar measurements, a simulated satellite acquisition, or scientific validation data.

## Behaviors exercised

- Competing hypotheses cite a shared synthetic measurement; the UI does not present reuse of that record as independent corroboration.
- A non-distinguishing relationship and an interpretation limitation leave the water explanation unresolved.
- Mixed supporting and contradictory relationships leave the surface-state explanation unresolved.
- An explanation without assessed evidence remains `NOT_EVALUATED`.
- The quality prerequisite is classified separately from a new evidence search.
- The open water-observation search targets exactly one hypothesis and states expected, weakening, and inconclusive outcomes plus acceptance gates and non-target hypotheses.
- A deliberately directional water disposition is rejected by the shared contract when its relationships remain non-distinguishing or limiting.
- The browser renderer displays the synthetic scope and, after opening the shared-evidence disclosure, the explicit non-independence warning. It also displays the targeted pre-registered test design.

## Verification

- `.venv/bin/python -m pytest tests/test_investigation_scenarios.py tests/test_investigation.py -q` — **50 passed**.
- `.venv/bin/python -m pytest -q` — **300 passed**.
- Firefox headless through the local application — **6 scenario-rendering checks passed**.
- `git diff --check` — passed.

## Limits

The fixture evaluates how the workflow handles analyst-assigned relationships, evidence links, unresolved states, and follow-up structure. It does not assess whether a relationship is scientifically true, whether a product passes provider QA, whether a SAR change algorithm is accurate, or whether a proposed observation is actually available or useful. The real T163 case remains a separate diagnostic Sentinel-1/OPERA investigation, and no synthetic result is included in production case data.
