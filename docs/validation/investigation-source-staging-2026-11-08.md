# Investigation source staging

**Result:** A draft can retain an additional local JSON source record while keeping its review state and all hypothesis relationships unchanged.

## Behavior

- The user selects a local JSON record from the open draft.
- ECHO checks that it is a JSON object with a `record_type`, computes a canonical JSON SHA-256, assigns a stable content-derived identifier, and records the local attachment time and ingest method.
- The record is labeled `USER_SUPPLIED_SOURCE_NOT_REVIEWED`; its review state remains `NOT_REVIEWED`, and its independence state remains `NOT_ASSESSED`.
- The inspector distinguishes user-declared source status from a verified provider disposition.
- The source appears in the draft's source list and evidence dependency view, and its exact parsed JSON can be inspected and exported with the draft.
- No hypothesis references, evidence relationships, dispositions, or follow-up availability are changed by staging.
- Repeated content, malformed records, modified embedded source content, inconsistent staging history, and attempts to turn an unassessed draft into a directional assessment are rejected.

## Verification

```bash
.venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q
.venv/bin/python -m pytest -q
git diff --check
```

Focused tests: **40 passed**. Full software suite: **312 passed**. `git diff --check`: passed.

A headless Firefox check created an unassessed draft from a controlled `QA_HELD` GCOV fixture, staged a second local JSON record through the interface and API, then confirmed the page displayed `NOT_REVIEWED`, `NOT_ASSESSED`, and `USER-DECLARED STATUS` while both hypotheses remained without evidence relationships. This is a UI and data-contract exercise, not an Earth observation, provider authentication, scientific source review, or validated investigation.

## Limits

The staging route accepts a supplied JSON record and does not retrieve or authenticate its claimed source. It does not test whether its spatial or temporal scope matches the investigation, whether its provider is authoritative, whether its QA is adequate, or whether it is independent of the SAR observations. Staged content has no effect on a scientific interpretation until a later source-specific review and analyst-assessment workflow is implemented.

See [Decision 0059](../decisions/0059-stage-unreviewed-sources-in-investigation-drafts.md).
