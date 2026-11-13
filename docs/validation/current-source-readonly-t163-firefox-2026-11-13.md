# Current-source read-only T163 Firefox walkthrough — 2026-11-13

## Setup

The current local checkout was served on loopback in curated single-case
read-only mode:

```bash
.venv/bin/echo serve \
  --host 127.0.0.1 --port 8771 \
  --data-root /home/mahdi-kheirddine/Projects/echo-dancing-with-the-sars-2026 \
  --case-file data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json \
  --read-only-demo
```

Firefox 158.0.1 used a proxy directed at unreachable loopback port 9 for
external HTTP/HTTPS, with `127.0.0.1`, `localhost`, and `::1` bypassed. The
temporary service was stopped after the walkthrough. The normal interactive
workbench on port 8766 was not restarted or stopped.

## Results

- `GET /api/cases`, `/api/case`, `/api/review`,
  `/api/cross-sensor-assessment`, `/api/adversarial-challenge`, and
  `/api/dswx-context` returned HTTP 200.
- `GET /api/investigation-drafts` returned HTTP 403 `READ_ONLY_DEMO`.
- `POST /api/catalog` returned HTTP 403 `READ_ONLY_DEMO`.
- Firefox showed the T163 case, a rendered geographic map, the curated
  read-only banner, and the one-case selector. It opened the investigation
  assessment and exposed all six hypothesis challenge controls.
- Selecting `H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE` opened the actual
  adversarial challenge. The UI retained `NOT TESTABLE` and `PROVIDER QA
  UNRESOLVED` dispositions.
- Browser API activity was exactly three local GET requests:
  `/api/cross-sensor-assessment`, `/api/investigation-evidence`, and
  `/api/adversarial-challenge`. No writes, provider calls, page errors, or
  external requests were observed.

This verifies the current-source read-only application path and linked
investigation interaction on the development host without Earthdata access.
It does not establish operation on another machine, an accepted physical
interpretation, or a validated SAR change result. The underlying T163 OPERA
RTC-S1 comparison remains diagnostic because its provider QA has no
consolidated verdict.

The checkout was dirty during this test. HEAD identifies its base revision;
this note does not claim that the commit alone reproduces the exact worktree.
