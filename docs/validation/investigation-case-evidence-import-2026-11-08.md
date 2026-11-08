# Investigation case-evidence import validation — 2026-11-08

## Scope

Verified importing eligible evidence from the retained T163 OPERA RTC-S1 case into an analyst-authored investigation draft. This validates local workflow and record integrity, not provider authenticity or scientific conclusions.

## Evidence

- `.venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q --tb=short` — **43 passed**.
- `.venv/bin/python -m pytest -q --tb=short` — **315 passed**.
- `.venv/bin/python -m compileall -q echo tests` — passed.
- `git diff --check` — passed.
- Headless Firefox end-to-end flow against the local app and retained T163 case: listed 10 eligible records; imported `NASA-OPERA-DSWX-HLS` with role `OPTICAL_PRODUCT_CONTEXT` and status `NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION`; preserved its case path and checksum; UI displayed `PROVIDER NOT REVERIFIED`. The analyst recorded `LIMITS_INTERPRETATION`; the draft disposition remained `UNRESOLVED`, source independence `NOT_ASSESSED`, and UI status `Analyst relationships recorded. Source validation and scientific interpretation remain unverified.`
- API negative checks: changing the retained assessment checksum after import returned HTTP 409; changing the draft's SAR scene IDs so they no longer matched the case assessment also returned HTTP 409.
- Browser checksum regression check: imported source JSON is retained as exact text, preserving the original file hash through the browser round trip. The parsed source remains available to the evidence inspector.

## What this verifies

- Only evidence linked from the active case's validated assessment and matching exact OPERA RTC-S1 pair is offered; direct evidence with unresolved derivation or shared-observation lineage is excluded.
- Imported case role, status, source identity, assessment identity, relative paths, checksums, and import time remain attached to the draft.
- Assessment rechecks the active case record and imported sources, so ordinary changes invalidate the requested review.
- Imported sources remain distinct from primary SAR and from user-supplied unreviewed records. No source role, status, provider QA, or analyst relationship is silently upgraded.
- The case-source picker explicitly says that absence of recorded derivation/shared-observation links does not establish source independence; imported source records keep independence `NOT_ASSESSED`.

## Limitations

- The workflow uses retained local case records and does not contact NASA, ASF, or another provider during import.
- A valid local assessment/checksum chain does not establish provider authenticity, scientific fitness for a hypothesis, independence, or claim truth.
- The tested optical source is contextual evidence, not validation of a SAR-derived boundary or measurement.
- Exact-pair eligibility currently applies to OPERA RTC-S1. Drafts remain local/export-only and analyst assessments remain unverified.
