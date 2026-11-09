# Multi-candidate follow-up screening

Date: 2026-11-09

## Result

One registered investigation test can now retain multiple candidate source screens. Each source is checked against the identical ordered acceptance gates. The draft retains source-linked screening checksums and history, and keeps hypothesis states `NOT_EVALUATED` until a separate assessment records explicit source relationships.

## Verification

- A focused regression screened one staged source with a failed gate, staged a second candidate after that result, then screened the second with all declared gates met. The draft retained both ordered source IDs and both distinct gate records; the aggregate follow-up state became `ANALYST_SCREENED_CANDIDATE` because one candidate met every analyst-declared gate. Both hypotheses remained `NOT_EVALUATED`.
- The same regression rejects re-screening a source already in the history and rejects tampering with the screening record checksum.
- The multi-candidate draft was saved and reopened through the local content-addressed draft store; the complete screening history and source links round-tripped unchanged. A legacy single-screen record without `screening_history` also remains valid.
- `PYTHONPATH=. .venv/bin/python -m pytest -q --tb=short` — **413 passed**.
- GJS rendered a two-candidate record and asserted that both candidate disclosures, their distinct `NOT_MET` and all-gates-met outcomes, the analyst-only limitation, and the explanation that gate outcomes do not transfer between sources were visible.
- GJS parsed `echo/static/app.js` and `echo/static/investigation.js`; `git diff --check` passed.

## Limits

The screen is a source-by-source comparison against one analyst-authored test plan, not a scientific ranking or source-validation service. It does not retrieve data, authenticate providers, determine independence, assign evidence relationships, evaluate hypotheses, or change a scientific conclusion. The browser interaction path was not exercised in this change; the underlying API, screening model, and shared reasoning renderer were tested.
