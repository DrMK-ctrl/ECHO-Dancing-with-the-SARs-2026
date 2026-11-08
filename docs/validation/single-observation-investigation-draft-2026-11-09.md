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
- A headless Firefox walkthrough selected the single NISAR timeline observation, loaded the retained Iraq preview through the map control, displayed its `FAIL` and `QA-HELD DIAGNOSTIC PREVIEW` status, opened **START INVESTIGATION**, and submitted two analyst-authored hypotheses and a discriminating follow-up through the local API. The returned draft retained the exact NISAR scene record and checksum, `DESCRIPTIVE_NISAR_SINGLE_OBSERVATION`, `QA_HELD_DIAGNOSTIC_PREVIEW`, `NOT_EVALUATED` hypotheses, and the `no temporal change` interpretation limit.
- The browser walkthrough used an isolated one-scene catalog fixture and intercepted only the preview retrieval route to serve the retained authentic preview record. The draft-creation API and browser interface ran normally; no external product was fetched, no persistent draft was saved, and no QA status was changed.

## Limits

This verifies the browser-to-API draft workflow with a real retained source record and preserves the non-directional QA boundary. It does not re-fetch or authenticate the submitted preview, independently validate provider QA, establish temporal change, validate a hypothesis, or demonstrate a causal finding. The fixture route isolates this UI and API integration from Earthdata access and product retrieval.
