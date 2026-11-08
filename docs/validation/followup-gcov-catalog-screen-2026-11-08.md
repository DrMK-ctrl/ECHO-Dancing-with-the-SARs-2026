# Follow-up GCOV catalog screen validation — 2026-11-08

## Scope

Verified the connection from an open investigation-draft follow-up to a metadata-only ASF NISAR GCOV search record. No new live ASF search or radar pixel retrieval was performed in this validation.

## Checks

- The draft service accepts only a structurally consistent ASF NISAR GCOV catalog record with matching feature counts, response checksum, and search-result state.
- The retained source links to the exact follow-up ID, target hypothesis, and canonical test-design SHA-256.
- Test compatibility and source independence are explicitly retained as not assessed; the interface presents this as optional availability discovery and asks the analyst to assess relevance.
- Attachment adds the catalog record to follow-up evidence references. A zero-result screen records `SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE`; one or more returned scenes record `CANDIDATE_RETRIEVED_UNASSESSED`. Hypothesis states and evidence relationships remain unchanged.
- A catalog-only record cannot be assigned a directional hypothesis relationship or used to screen follow-up acceptance gates.
- The local HTTP endpoint accepts a valid record and returns the linked draft; the static interface exposes a specific follow-up context panel.
- A headless Firefox walkthrough exercised the follow-up button, search dialog, submission, returned draft, and source inspector using a deterministic zero-match response fixture. It verified that the display labels the result metadata-only, retains the source reference, and leaves hypothesis and test-gate assessment unassessed.

## Result and limits

The focused regression run `tests/test_investigation_draft.py tests/test_web.py` passed: **57 passed**. The full suite passed: **357 passed**. The Firefox walkthrough used a deterministic local zero-match fixture. These checks verify application flow and science-boundary enforcement, not NASA service availability, product authenticity, observation suitability, or pixel measurements. A catalog feature count indicates matching metadata only. No change result or scientific conclusion is produced.
