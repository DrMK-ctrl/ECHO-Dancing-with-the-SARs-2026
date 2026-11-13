# Catalog request validation and size guard — 2026-11-13

## Live API smoke check

Against the local interactive workbench at `127.0.0.1:8766`, a GCOV catalog request with latitude `91` returned HTTP `400` and the WGS84 range message. An 8 KiB-plus-one JSON request returned HTTP `413` with the catalog body-size error. The route validates bounds before invoking catalog search and checks the request length before parsing the body; neither probe reached ASF or changed application records.

## Automated boundary regression

`tests/test_web.py::test_catalog_endpoint_enforces_request_body_limit_at_boundary` runs the catalog endpoint on loopback with a mocked ASF search. A valid JSON request padded to exactly the configured 8 KiB limit succeeds and reaches the mock once. A request one byte over the limit receives HTTP `413`; the mock call count remains unchanged.

Verification on the local checkout:

- Focused boundary test: **1 passed**.
- Full suite: `.venv/bin/python -m pytest -q` — **499 passed in 36.26s**.
- `git diff --check` — clean before commit.

This covers the ASF GCOV catalog route's request-size boundary and invalid latitude handling. The route limits also received a live boundary-rejection sweep across all 21 interactive POST endpoints.

## Live all-route oversize-header sweep

The running interactive workbench at `127.0.0.1:8766` received one POST per API route with `Content-Length` set to that route's configured maximum plus one byte. No request body was sent. Each route returned HTTP `413` before body parsing, provider dispatch, or record mutation. The Bhoonidhi probe included its required same-origin `Origin` header; without that header it correctly rejects the request as `403` before reaching size validation.

- Result: **21/21 routes returned HTTP 413**.
- The routes cover catalog searches, GCOV/OPERA analyses and previews, investigation draft creation/edit/assessment/evidence actions, QA summary/export, and counterfactual preview.
- This exercises the live request-size guards and dispatch ordering. It does not establish behavior for malformed bodies below the size limit, sustained load, or provider availability; those have separate tests and operational dependencies.
