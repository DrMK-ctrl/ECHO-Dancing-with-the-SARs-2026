# Investigation follow-up-source screen validation — 2026-11-08

## Scope

Verified attaching a staged source to the draft's preregistered next observation and recording analyst-declared acceptance-gate results. The exercised source is a controlled context JSON fixture; this validates the workflow, not the source or a scientific result.

## Evidence

- `.venv/bin/python -m pytest tests/test_investigation_draft.py::test_followup_screen_links_staged_evidence_without_evaluating_hypotheses tests/test_web.py::test_investigation_draft_api_preserves_source_and_rejects_unsupported_records tests/test_web.py::test_investigation_draft_imports_only_validated_case_sources_for_exact_sar_pair -q --tb=short` — **3 passed**.
- `.venv/bin/python -m pytest -q --tb=short` — **317 passed**.
- `.venv/bin/python -m compileall -q echo tests` and `git diff --check` — passed.
- Targeted unit/API tests cover all gates met, an unknown or failed gate, missing and reordered gates, a primary SAR source rejection, altered screening hashes, active-case revalidation, and preservation of hypothesis state and source status.
- Headless Firefox workflow against the local app used the retained diagnostic T163 OPERA RTC-S1 pair as the draft's primary record and a controlled user-supplied context JSON source for the follow-up. The analyst marked source-quality state `UNKNOWN`, with the other gates `MET`; the rendered follow-up state was `RETRIEVED_QUALITY_LIMITED`, visibly labeled `ANALYST SCREEN · UNVERIFIED`. The hypothesis remained `NOT EVALUATED`.
- The browser status message explicitly stated the screen was analyst-declared and the hypothesis state unchanged.
- Full suite and static checks are recorded after the final run below.

## What this verifies

- The screening record binds one staged source checksum to all pre-registered gates and records review basis, limitations, timestamp, and record checksum.
- `ANALYST_SCREENED_CANDIDATE` requires every analyst-entered gate to be `MET`; any `NOT_MET` or `UNKNOWN` result yields `RETRIEVED_QUALITY_LIMITED`.
- Gate-screening does not change source role, source review state, independence, provider QA/status, or hypothesis assessment.
- The screened source can subsequently enter the separate explicit analyst relationship workflow.

## Limitations

- The analyst is unauthenticated, and ECHO does not verify that declared gate outcomes are correct.
- The controlled context JSON is not a real independent observation. The diagnostic OPERA pair remains nonvalidated and is not directionally reassessed by this workflow.
- Only one source-screen record is allowed per draft's single planned observation; source comparison and review revisions are future work.
- This does not retrieve external evidence, automatically evaluate data suitability, produce a validated finding, or establish that a candidate is scientifically discriminating.
