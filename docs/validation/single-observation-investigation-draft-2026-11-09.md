# Single-observation NISAR investigation draft — 2026-11-09

## Result

The retained real P05023 NISAR GCOV single-observation preview can now start a source-linked investigation draft through the local HTTP API. The provider QA `FAIL` and `QA_HELD_DIAGNOSTIC_PREVIEW` disposition remain unchanged. The draft retains the exact preview record and checksum, leaves its hypotheses `NOT_EVALUATED`, leaves its follow-up `NOT_SEARCHED`, and states that one acquisition does not establish temporal change.

## Evidence

- Source: [`nisar-iraq-p05023-hhhh-preview-2026-11-08.json`](../../data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json), an authentic ASF NISAR GCOV preview retrieved through ECHO's bounded reader; the retained ASF provider-QA status is `FAIL`.
- The builder validates the provider, mission, product and scene identity; ties the catalog identity and product URL to the exact scene; verifies the provider-QA status, artifact URI, and SHA-256 relationships; and checks that the measurement and quality arrays match the declared bounded grid.
- Single-observation evidence uses the distinct role `DESCRIPTIVE_NISAR_SINGLE_OBSERVATION`, which the shared contract and analyst interface treat as non-directional. A proposed `SUPPORTS` assessment is rejected.
- The local HTTP API integration test submitted the real preview record and received an unassessed draft with intact source text and the one-observation limitation.

## Verification

- Focused investigation, scenario, and web suites: **120 passed** (`tests/test_investigation_draft.py`, `tests/test_investigation.py`, `tests/test_investigation_scenarios.py`, `tests/test_web.py`).
- Python compilation: passed for the changed application and test modules.
- `gjs` parsed the served `app.js` source successfully.
- `git diff --check`: passed.

## Limits

This verifies draft creation, structural source linkage, and the non-directional QA boundary through a real retained source record and a local API. It does not re-fetch or authenticate the submitted preview, validate provider QA independently, establish a temporal change, test browser interaction, validate a hypothesis, or demonstrate a causal finding. The map button is rendered by the existing preview inspector; the focused browser interaction was not exercised in this check.
