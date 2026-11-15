# Bounded GCOV preview reuse within a browser session — 2026-11-13

## Change

The investigation workspace can now restore the last eligible bounded NISAR
preview from in-memory browser-session state when the requested scene URL,
exact WGS84 AOI bounds, frequency, and diagonal measurement layer all match.
The cache holds at most one preview and only retains windows of 16,384 cells or
fewer. Larger windows are displayed normally but are not kept as a second
in-memory copy. The cache is neither written to disk nor sent to a service.

The restored record retains its original source and provider-QA timestamps. A
toast states the QA retrieval time and explicitly says that no provider request
was made and QA was not refreshed. A changed area, measurement layer, frequency,
scene, or product URL does not match the cache key. This is a repeat-view
latency improvement; it does not reduce the latency of a first live read.

## Browser verification

The current checkout was served locally at `127.0.0.1:8768`, using the Iraq
case. Firefox ran
`tools/validation/check_gcov_preview_browser.py` with the retained current-source
Beirut NISAR preview and catalog records as local fixtures. The browser loaded
and rendered the real retained HHHH measurement record, opened its source
inspector, hid and restored the preview, and confirmed:

- only one preview fixture request occurred across the original display and
  exact repeat view;
- the toast retained the QA retrieval timestamp and disclosed that QA was not
  refreshed;
- a changed AOI or layer generated a different cache key;
- a 129 × 128 window was rejected by the cache-size bound;
- the provider `FAIL`, diagnostic-only disposition, measurement attributes,
  pixel inspection, and source hashes remained visible;
- no browser errors occurred.

The Firefox run passed all **13 checks**. The full automated suite then passed
`.venv/bin/python -m pytest -q` with **537 passed in 42.07 seconds**. The suite
does not independently validate the science or live-provider behavior of this
session-cache change.

This was a Firefox UI replay with local fixture responses. It did not make an
ASF request, benchmark live network latency, or alter the retained measurement
record. The cache lasts only for the current page lifetime; a reload or new tab
requires retrieval again. The test does not establish a general browser-memory
budget beyond the single-preview cell-count bound.
