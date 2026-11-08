# Source-linked investigation draft workflow

**Result:** Pair-analysis records can enter a browser-driven, unassessed investigation plan with one falsifiable, hypothesis-specific next observation.

## Exercised behavior

- The GCOV and OPERA pair inspectors offer **Start investigation draft**.
- The analyst enters a question, two competing hypotheses, each hypothesis's scope, expected observation, weakening condition, and evidence need.
- The analyst selects one hypothesis for a proposed next observation and records the search action, discriminating question, expected and weakening observations, inconclusive condition, acceptance gates, interpretation limit, possible interpretation, and reason for prioritizing the test.
- ECHO creates a source-linked record with canonical JSON SHA-256, retains the submitted pair record, and renders the hypotheses and planned workstream through the shared investigation renderer.
- The source status remains visible in the record. Each hypothesis remains `NOT_EVALUATED`; its evidence references and assessments remain empty. The proposed follow-up remains `NOT_SEARCHED` with one test target.
- The record can be inspected and downloaded as JSON. It is not persisted by the local server.

## Verification

From the repository root:

```bash
.venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q
.venv/bin/python -m pytest -q
git diff --check
```

Results at this checkpoint: focused tests **38 passed**; full suite **310 passed**; `git diff --check` passed.

A headless Firefox session loaded the local ECHO interface, opened the draft dialog using a controlled `QA_HELD` GCOV pair fixture, completed two hypotheses and a next-observation design, and submitted it through the local API. The rendered output showed `DRAFT_NOT_ASSESSED`, the user-selected target hypothesis, and a `NOT_SEARCHED` follow-up. This validates interface and contract integration only. The fixture is not an observation, no satellite retrieval occurred during the browser check, and no scientific hypothesis was evaluated.

## Limits and next validation

The pair record is accepted as submitted and checksummed; provider re-fetch, persisted draft storage, source retrieval for planned observations, and scientific-suitability assessment are not implemented here. The analyst-authored relationships and test design are structurally validated, not scientifically endorsed. The QA-held NISAR route remains a planning workflow and does not create a measurement. The OPERA route remains diagnostically classified. The next substantive step is a source-aware path for attaching retrieved follow-up evidence, validating its provenance and suitability, and then recording explicit analyst-reviewed evidence relationships without treating provider credibility as proof of an interpretation.

See [Decision 0058](../decisions/0058-start-source-linked-investigations-from-pair-records.md).
