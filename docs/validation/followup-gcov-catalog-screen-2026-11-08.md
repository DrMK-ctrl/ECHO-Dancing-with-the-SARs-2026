# Follow-up GCOV catalog screen validation — 2026-11-08

## Scope

Verified the connection from an open investigation-draft follow-up to a metadata-only ASF NISAR GCOV search record. No new live ASF search or radar pixel retrieval was performed in this validation.

## Checks

- The draft service accepts only a structurally consistent ASF NISAR GCOV catalog record with matching feature counts, response checksum, and search-result state.
- The retained source links to the exact follow-up ID, target hypothesis, and canonical test-design SHA-256.
- Attachment leaves the follow-up availability state, hypothesis state, and evidence relationships unchanged.
- A catalog-only record cannot be assigned a directional hypothesis relationship or used to screen follow-up acceptance gates.
- The local HTTP endpoint accepts a valid record and returns the linked draft; the static interface exposes a specific follow-up context panel.
- A headless Firefox walkthrough exercised the follow-up button, search dialog, submission, returned draft, and source inspector using a deterministic zero-match response fixture. It verified that the display labels the result metadata-only and keeps the test state unchanged.

## Result and limits

The focused regression run `tests/test_investigation_draft.py tests/test_web.py` passed: **56 passed**. The full suite passed: **356 passed**. The Firefox walkthrough used a deterministic local zero-match fixture. These checks verify application flow and science-boundary enforcement, not NASA service availability, product authenticity, observation suitability, or pixel measurements. A catalog feature count indicates matching metadata only. No change result or scientific conclusion is produced.
