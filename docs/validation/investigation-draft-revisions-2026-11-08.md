# Iterative investigation draft revisions — 2026-11-08

## Result

An assessed investigation can now be continued as a linked, unassessed round. The saved parent remains unchanged; the child carries its source records and provenance, clears prior hypothesis relationships, and requires a new falsifiable next-observation design.

## Verification

- Focused draft, store, and web API tests: **50 passed**.
- Full software suite: **322 passed**.
- Python compilation and `git diff --check`: passed.
- Firefox headless walkthrough: loaded a saved assessed parent, opened the new-round form, created a round targeting a different hypothesis, confirmed the displayed parent checksum and unassessed state, and saved the child. All four checks passed.
- The API test also creates and stores two successive revision rounds, verifies the parent chain after reopen, rejects a mismatched or unavailable parent reference, and confirms the original assessed snapshot remains byte-identical.

## Scope and limits

The child preserves the same primary SAR pair and staged source records; this feature does not acquire a new observation or create a new measurement. It clears analyst relationship labels so they must be reviewed again in the new round. The user supplies the next test and assessments. Parent-chain integrity is checked against saved local snapshots, not a remote identity or analyst signature. Scientific QA, source independence, evidence suitability, and causal interpretation remain separate review responsibilities.
