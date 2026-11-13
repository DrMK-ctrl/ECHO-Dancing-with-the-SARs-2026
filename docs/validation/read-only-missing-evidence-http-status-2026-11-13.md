# Read-only missing-evidence HTTP status — 2026-11-13

## Finding and change

The curated read-only T163 case has a retained case review and cross-sensor
assessment, but no case-specific NISAR diagnostic preview or `qa-review.json`.
The routes previously returned HTTP 503 for the absent preview and HTTP 500 for
the absent QA record. These are expected absence states, not service failures.
The routes now return explicit HTTP 404 responses with stable codes:
`NO_RETAINED_DIAGNOSTIC_PREVIEW`, `NO_RETAINED_QA_REVIEW`, and
`NO_RETAINED_CASE_REVIEW`. Invalid, oversized, mismatched, or integrity-failed
records retain their failure paths.

## HTTP and browser verification

An isolated loopback server using the T163 retained case returned:

- `/api/qa`: HTTP 404 `NO_RETAINED_QA_REVIEW`.
- `/api/diagnostic-preview`: HTTP 404 `NO_RETAINED_DIAGNOSTIC_PREVIEW`.
- `/api/review`: HTTP 200 with the retained case review.
- `/api/cross-sensor-assessment`: HTTP 200 with the retained assessment.

Headless Firefox 158.0.1 loaded the curated T163 page from the current source,
rendered the geographic SVG map, and opened **Open Case Investigation**. The
dialog displayed the retained Sentinel-1/OPERA backscatter and NASA DSWx-HLS
context, with the causal interpretation still unresolved. No provider request
or draft mutation was made during this browser check.

The visible catalog detail says that no catalog acquisitions match this case's
catalog query; the retained investigation remains available separately. The
page startup does not treat its absent NISAR preview as a broken service.

## Regression verification

- `.venv/bin/pytest -q` — **524 passed in 41.01 seconds**.
- `git diff --check` — passed.

This validates the missing-evidence status behavior and one retained T163 browser
workflow. It does not replace the broader clean-account or all-route release
acceptance checks.
