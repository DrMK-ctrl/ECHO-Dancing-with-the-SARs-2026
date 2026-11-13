# Read-only case sidecar boundary — 2026-11-13

## Finding

The curated server already constrained its selected catalog and manifest-linked
evidence, but `/api/review`, `/api/qa`, and `/api/qa-reports` opened adjacent
JSON sidecars without checking whether a symlink escaped the selected case.
That could expose a file outside a curated case bundle or from a sibling case.

## Change

Sidecar paths are now resolved and required to remain inside the selected case
directory before the review and QA routes read them. The existing `serve`
read-only startup check continues to require the selected catalog under
`data/cases`; this path check does not replace that startup boundary.

## Verification

- Six live HTTP fixture cases attempted to serve review, QA, and QA-report
  sidecars linked either outside the bundle root or into another case folder.
  All returned HTTP 503 without returning the marker content.
- The curated case registry did not expose the linked external review identity.
- Existing review preference, reviewed-scene QA filtering, and curated-mode
  request-blocking tests passed.
- Full local suite: `.venv/bin/pytest -q` — **522 passed in 40.44 seconds**.

This closes the identified sidecar path escape. It is not a complete audit of
every read-only route or a clean-account distribution acceptance test.
