# Bhoonidhi S-SAR catalog map integration — 2026-11-08

## Result

ECHO's local workspace now connects its bounded Bhoonidhi NISAR S-SAR GCOV catalog client to the selected map area. A dedicated dialog sends credentials and a bounded date/area query to a same-origin loopback endpoint. Returned features appear as a distinct footprint layer and separate timeline lane; selecting an item opens its provider, mission, collection, item ID, acquisition time, online status, and source record. The UI explicitly reports that product QA and radar pixels have not been retrieved.

This validates the software integration with a controlled synthetic STAC feature. It is not a live Bhoonidhi query, a real S-SAR observation, product-access verification, QA assessment, or scientific measurement. The user has not reported an active Bhoonidhi account, so live catalog coverage remains unverified.

## Boundaries and safeguards

- The endpoint accepts POST requests only from a loopback-bound ECHO server and a matching HTTP loopback Origin/Host. It caps the request body, checks WGS84 bounds, timezone-aware dates, page size, and page cap, and calls the existing provider-specific client.
- Credentials and the returned bearer token are held only for the request path. ECHO clears the credential fields and request payload references and does not put credentials in browser storage, source records, or repository files.
- The catalog client restricts pagination links to the official HTTPS Bhoonidhi search endpoint. A page-capped response remains explicitly incomplete.
- Returned properties remain raw provider metadata in the source record. The UI does not convert them to ASF records or infer QA, pixel availability, polarization semantics, or change.
- S-SAR footprints have separate styling and a separate timeline. An AOI change clears the prior S-SAR result so old catalog coverage is not presented against a new query area.

## Verification

- `.venv/bin/python -m pytest tests/test_web.py tests/test_bhoonidhi.py -q --tb=short` — **51 passed**, covering endpoint, origin checks, transient credentials, client behavior, and pagination.
- `.venv/bin/python -m pytest -q --tb=short` — **353 passed** across the full repository.
- `.venv/bin/python -m compileall -q echo tests` and `git diff --check` — passed.
- Firefox headless with the local ECHO server and a mocked provider adapter — opened the search dialog for the retained WGS84 AOI, submitted test-only credentials, received a controlled synthetic partial-page result, rendered one S-SAR timeline item and an in-view polygon at its supplied coordinates, displayed the page-cap warning and `PRODUCT QA: NOT RETRIEVED` / `MEASUREMENT: NOT RETRIEVED`, and cleared both credential form fields. The source-record dialog showed the provider identity and synthetic item ID; a 390 px viewport wrapped the map controls.
- `git diff --check` and `.venv/bin/python -m compileall -q echo tests` — passed.

The focused tests use mocks and do not demonstrate actual Bhoonidhi authentication, STAC schema coverage, live provider pagination, or product availability. Node.js is not installed; JavaScript parsing and interaction were exercised by Firefox.
