# Investigation analyst-assessment validation — 2026-11-08

## Scope

Validated the local draft workflow that records analyst-entered relationships between a retained source record and an authored hypothesis. This is software workflow verification, not scientific validation of any source or relationship.

## Evidence

- `.venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q` — **42 passed**.
- `.venv/bin/python -m pytest -q` — **314 passed**.
- Headless Firefox workflow through the local interface and API: created a draft from a controlled QA-held GCOV fixture, entered a `LIMITS_INTERPRETATION` relationship, supplied the inspection basis and limits, and recorded the assessment. The rendered state was `DRAFT_ANALYST_ASSESSED_UNVERIFIED`; the derived state was `UNRESOLVED`; the record retained provider QA `FAIL`; and the UI showed the inspection basis and stated limits.
- Headless Firefox source-selection behavior: a QA-held pair defaulted to `LIMITS_INTERPRETATION` and disabled directional `SUPPORTS`; `LIMITS_INTERPRETATION` saved successfully with the same QA-retention and display results above.
- Headless Firefox staged-source behavior: `SUPPORTS` remained disabled for the QA-held pair; after selecting a staged context record it stayed disabled while fit was `UNKNOWN`, then became available after selecting analyst-declared `SUITABLE_FOR_STATED_SCOPE`. The resulting draft was `DRAFT_ANALYST_ASSESSED_UNVERIFIED` / `SUPPORTED_WITHIN_SCOPE`, while the source remained `NOT_REVIEWED` and independence remained `NOT_ASSESSED`; the interface displayed the unverified status.
- Backend negative checks: directional relationships without `SUITABLE_FOR_STATED_SCOPE` are rejected; even with that analyst-declared fit, QA-held and diagnostic SAR records are rejected for directional use.
- `git diff --check` — passed.

## What this verifies

- API inputs are restricted to known source and hypothesis IDs, unique source-hypothesis pairs, enumerated relationships and source-fit states, and substantive analyst rationale, inspection basis, and limitations.
- The source hash is bound to each relationship. The assessment ledger has a canonical SHA-256 to detect mismatched edits; neither checksum authenticates authorship or proves scientific correctness.
- The existing deterministic rule derives only the disposition implied by recorded relationships; it emits no confidence or probability.
- Directional relationships require the analyst to mark evidence suitable for the stated scope. QA-held, product-maturity-held, descriptive-only NISAR, diagnostic OPERA, and no-common-valid-pixel SAR roles remain non-directional regardless of that selection. Their provider QA and maturity records remain unchanged.
- Analyst-assessed draft records can be exported, but they are not persisted to the case assessment store. Staged source review and independence remain unassessed.

## Limitations

- The local reviewer is unauthenticated; a user can enter any relationship and review basis.
- No provider record is re-fetched or the analyst-declared source fit, independence, spatial-temporal relevance, or claim truth verified by this workflow.
- A disposition such as `SUPPORTED_WITHIN_SCOPE` summarizes analyst-entered relationship and fit labels only, including when the retained source is still `NOT_REVIEWED`; it must not be presented as a validated scientific finding.
- This does not yet complete an end-to-end real-data investigation. Current source staging accepts local JSON records; source-specific retrieval and qualification remain separate work.
- The headless browser check was run against a controlled QA-held fixture, not authentic satellite measurements.
