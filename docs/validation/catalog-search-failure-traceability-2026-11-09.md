# Catalog search failure traceability — 2026-11-09

## Change

ASF GCOV catalog requests that fail before returning a result now return a safe, structured attempt record with the exact effective query and start/end timestamps. The response omits the raw exception. It identifies ECHO as the observer and ASF as the target provider; it does not claim ASF supplied an authoritative no-match response.

When the request is part of an open investigation follow-up, the interface attaches the attempt to that follow-up. The retained entry is checksummed and linked to the pre-registered test design. Its availability state is `SEARCH_FAILED_RETRYABLE`, visibly distinct from a successful search returning zero candidates. The attempt is metadata about a request, not scientific evidence: it creates no evidence artifact or hypothesis relationship and does not change any hypothesis state. A successful retry retains prior failed attempts alongside the resulting catalog record.

The UI shows the failed query's dates, maturity, point or bounds, status, and checksum. The draft remains unsaved until the user saves a private local snapshot, consistent with other draft edits.

## Verification

- Tests exercise the catalog endpoint's safe failure response, including exact query retention and omission of raw exception details.
- Draft tests validate checksum and follow-up/test-design linkage, ensure failed attempts cannot enter evidence references, reject tampering, and verify failed-then-successful retry history.
- Web/API tests exercise failure attachment and successful retry attachment.
- `PYTHONPATH=. .venv/bin/pytest -q`: 376 passed.

## Limits

Failure behavior was exercised with a controlled test double; this does not claim a new live ASF timeout or provider-side error classification. The recorded state means ECHO's request returned no usable catalog result. It is not evidence that observations are absent, and does not change any scientific QA or result disposition. Attempt records are ECHO-generated and locally checksummed; they are not signed by ASF.
