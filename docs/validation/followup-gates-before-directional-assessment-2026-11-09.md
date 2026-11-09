# Follow-up gate enforcement in investigation assessment

Date: 2026-11-09

## Result

For the hypothesis explicitly targeted by a registered follow-up test, staged candidates with a missing screen or any failed/unknown gate cannot be assigned directional support or contradiction. Candidates meeting every analyst-declared gate can proceed only after a separate analyst fit declaration. The source remains unreviewed and unverified; the assessment remains analyst-authored.

## Verification

- Added backend coverage for an unscreened source, a candidate with a failed gate, a candidate with all gates met, non-directional use after a failed screen, and a tampered assessed record whose screen is changed to fail.
- Confirmed legacy assessment records with the previous method remain readable; newly recorded assessments use the gated method marker.
- `PYTHONPATH=. .venv/bin/python -m pytest tests/test_investigation_draft.py -q --tb=short` — **26 passed**.
- `PYTHONPATH=. .venv/bin/python -m pytest -q --tb=short` — **414 passed**.
- Headless Firefox against the local ECHO page and API confirmed that a failed candidate disables directional relation choices and shows why; an all-gates-met candidate permits a directional relation only after `SUITABLE_FOR_STATED_SCOPE` is selected. The rendered result remained `ANALYST ASSESSMENT · UNVERIFIED` and `SUPPORTED WITHIN SCOPE`.
- `.venv/bin/python -m compileall -q echo tests` and `git diff --check` passed.

## Limits

This is workflow enforcement, not automated product QA. The gate values and evidence fit are entered by an unauthenticated analyst. Passing them does not verify source authenticity, independence, measurement quality, relevance, or causation. The controlled browser records were test fixtures, not Earth observations.
