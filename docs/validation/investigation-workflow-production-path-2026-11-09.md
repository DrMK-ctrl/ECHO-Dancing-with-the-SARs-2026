# Controlled execution through the investigation workflow

Date: 2026-11-09

## Purpose

The existing ambiguity fixture checked the reusable investigation contract directly. It did not execute the production draft-creation, source-staging, follow-up-screening, or analyst-assessment functions together. This test exercises that path with controlled software records to verify that the workflow preserves mixed evidence and quality boundaries.

## Scenario and result

The test creates a draft around a record marked `QA_HELD`, with no measurement arrays and no change calculation. It stages two explicitly synthetic context records, records that they share a declared source dependency, screens both against one pre-registered test, and submits one supporting and one contradictory analyst relationship for the target hypothesis.

The resulting target hypothesis remains `UNRESOLVED`; the other hypothesis with no assessment remains `NOT_EVALUATED`. The primary SAR record remains `QA_HELD`, both candidate screens retain their exact checksums in the assessment, and all additional sources retain `independence_state: NOT_ASSESSED`.

## Verification

- `.venv/bin/python -m pytest tests/test_investigation_scenarios.py -q --tb=short` — **4 passed**.
- `PYTHONPATH=. .venv/bin/python -m pytest -q --tb=short` — **416 passed**.
- Python compilation and `git diff --check` passed.

## Limits

All records and relationships in the new scenario are controlled test fixtures. The test verifies deterministic workflow behavior, not whether a real source is suitable, whether its relationship is correct, or whether an Earth-surface mechanism caused a SAR response. It does not improve the QA status of any NISAR or OPERA product. ECHO still lacks a QA-cleared NISAR temporal comparison and an independently validated causal finding; the T163 OPERA case remains diagnostic and analyst-assessed.
