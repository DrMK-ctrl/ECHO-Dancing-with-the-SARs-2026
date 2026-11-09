# Investigation draft lineage

Date: 2026-11-09

## Change

Draft source staging now accepts optional analyst-declared `derived_from_evidence_ids` and `shares_source_observations_with` references to records already staged. The backend checks referenced IDs, duplicate and conflicting links, and derivation cycles. It stores the declaration on the artifact and in staging history, validates that both copies match, and preserves the existing `NOT_ASSESSED` independence state. Legacy drafts with empty lineage remain valid.

The source-staging interface presents two multi-select controls. The source list marks declared links as unverified and links each referenced record to the existing source inspector. No assessment relationship or hypothesis disposition is derived from lineage.

## Verification

- `PYTHONPATH=. .venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q --tb=short` — **68 passed**.
- `PYTHONPATH=. .venv/bin/python -m pytest -q --tb=short` — **415 passed**.
- Python compilation passed for `echo` and `tests`.
- GJS parsed `echo/static/app.js` successfully; `git diff --check` passed.
- Headless Firefox checks created an unassessed draft through the visible form, exposed both lineage selectors, rendered a linked draft with the unverified lineage label and target evidence ID, and opened the target record in the source inspector. The selector also rejects assigning one record both lineage types before opening the file picker.
- The API test staged a linked source and verified that artifact lineage and staging-history lineage matched; the draft tests verified unknown-ID rejection, cycle rejection, checksum/history consistency, and unchanged `NOT_ASSESSED` state.

These are application-workflow checks using controlled records. They do not establish that any declared lineage is factually correct or that any source is independent.

## Limits

Lineage is currently analyst-entered when the source is staged. ECHO does not discover dependencies automatically, resolve identifiers from another repository, or use lineage as a weight in the deterministic hypothesis disposition. Missing links remain unknown rather than evidence of independence. No retained Earth-observation finding or QA state changed.
