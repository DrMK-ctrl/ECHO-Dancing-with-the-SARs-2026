# Investigation-draft restore validation — 2026-11-08

## Scope

Verified that downloaded investigation drafts can be restored through the interface after structural, checksum, and current case-link checks. The browser case used diagnostic Sentinel-1/OPERA evidence and NASA optical context; it is workflow evidence, not a validated scientific conclusion.

## Evidence

- `.venv/bin/python -m pytest -q --tb=short` — **316 passed**.
- `.venv/bin/python -m compileall -q echo tests` — passed.
- `git diff --check` — passed.
- API check: a fully analyst-assessed draft with a case-imported DSWx-HLS source restored with identical content. Editing the embedded source without updating its SHA-256 was rejected with HTTP 422.
- API negative check: editing the imported source's case-assessment SHA-256 in both provenance copies was rejected with HTTP 409 because it no longer matched the active case's validated assessment.
- Headless Firefox end-to-end check: created an assessed draft from the T163 OPERA pair, imported the linked NASA DSWx-HLS context record, downloaded it to a local JSON file, and restored it through **Open saved draft JSON**. The UI showed `DRAFT_ANALYST_ASSESSED_UNVERIFIED`, retained `INDEPENDENCE NOT_ASSESSED` and `PROVIDER NOT REVERIFIED`, and reported that case links were rechecked.
- Browser round-trip regression: JavaScript numeric JSON serialization had changed primary-source canonical hashes. Draft creation now retains the exact source JSON text supplied by the browser; a `1.0` fixture and real browser round-trip both restored with their original byte checksum.

## What this verifies

- Saved drafts preserve their assessment, source identities, source roles, statuses, and checksum-bearing text across a browser session boundary.
- Corrupt or structurally inconsistent drafts are rejected before display.
- Case-linked source records must still match the selected case's validated assessment, exact SAR scene pair, source path, and checksum.
- Restored analyst assessments remain provisional and unverified.

## Limitations

- Drafts are still downloaded and selected manually; ECHO does not provide server persistence or autosave.
- A checksum does not authenticate the analyst or the provider and does not prove source independence or scientific correctness.
- The live restore flow was exercised with one retained T163 OPERA RTC-S1 case. The generic draft contract supports GCOV and OPERA pair records, but this browser check does not establish all product-specific scientific workflows.
