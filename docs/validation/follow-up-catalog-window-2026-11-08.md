# Follow-up catalog-window linkage — 2026-11-08

## Result

Investigation drafts can now retain an optional inclusive catalog-search date window in the single-hypothesis test design. The values are validated before record creation and included in the test-design checksum. Opening the linked ASF GCOV search pre-fills those dates; its context names the target hypothesis, planned dates, and metadata-only boundary. The actual catalog query remains editable and is retained verbatim as the search record.

## Verification

- Backend tests create a draft with a valid date window, reject a reversed window, and preserve legacy drafts without one.
- Firefox headless created a draft through the local application using a local QA-held SAR fixture; the draft rendered the dates `2026-10-25` through `2026-11-06` in its pre-registered test design. Opening its linked catalog dialog prefilled the same dates and showed the target hypothesis and editable-query context. No catalog request was sent.
- `.venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q` — **58 passed**.
- `.venv/bin/python -m pytest -q` — **359 passed**.
- `.venv/bin/python -m compileall -q echo` and `git diff --check` — passed.
- `git diff --check` — passed.

## Limits

This only connects the test's declared discovery interval to the query controls. It does not decide which dates or sensor are scientifically appropriate, prove a candidate scene covers the target, or change follow-up status. Existing drafts without a structured window remain supported.
