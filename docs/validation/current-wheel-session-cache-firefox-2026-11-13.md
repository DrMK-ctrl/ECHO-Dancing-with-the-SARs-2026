# Installed-wheel session-cache browser validation — 2026-11-13

## Result

The current Python wheel was installed into an isolated target directory and
served from outside the source checkout. Firefox replayed the retained Iraq
NISAR GCOV preview through the packaged application. **All 13 browser checks
passed.** This verifies that the current frontend is included in the wheel and
that the retained-preview workflow runs through the installed package.

## Artifact and runtime

- Wheel: `echo_sar_investigation-0.1.0-py3-none-any.whl`
- SHA-256: `040fc9fab71e1519ea6c10d664d253b14f4a6e59f17994fae862006669796ae6`
- Wheel size: 423,496 bytes; 46 files.
- Build: `python3 -m pip wheel --no-build-isolation --no-deps . --wheel-dir /tmp/echo-current-source-wheel-20261113`
- Installed under `/tmp/echo-wheel-installed-20261113` with `pip install --no-deps --target`.
- Runtime import resolved to `/tmp/echo-wheel-installed-20261113/echo/__init__.py`.
- Local service was launched from `/tmp` on `127.0.0.1:8770`, using the installed
  console entry point and the checkout's retained case data as an explicit data root.
- Firefox validation command:
  `.venv/bin/python tools/validation/check_gcov_preview_browser.py --url 'http://127.0.0.1:8770/?case_id=iraq-2026-nisar-gcov-diagnostic' --require-source-attributes`

## Verified browser behavior

The validation reported `PASS` for: raster rendering; AOI bounds; visible
provider QA failure and diagnostic disposition; actual sample-pixel inspection;
source-record inspection; fixture-only catalog and preview responses; reuse of
the same exact cached request within the tab session; cache-key changes for a
different area or layer; rejection of oversized previews from the cache; no
browser errors; validated hashes for source measurement and QA attributes; and
visible sample handling.

The inspected retained sample reported row 12971, column 5068, gamma-zero
30.9233 linear / 14.90 dB, mask 1, 5.190571308135986 looks, exception mask 0.
The browser labels the source `PROVIDER QA FAIL` and the product
`QA_HELD_DIAGNOSTIC_PREVIEW`; this test does not elevate it to an accepted
analysis. The exact cached-view notice states that the QA timestamp is retained,
no provider request was made on reuse, and QA was not refreshed.

## Limits

The browser test intercepted catalog and measurement responses with retained
local JSON records. No ASF/NASA service was contacted, no fresh pixels or QA
were retrieved, and the browser result is not independent scientific
validation. The data root was the project checkout, so this does not verify a
self-contained judge bundle or clean-account installation. It verifies wheel
packaging and one local installed-package workflow only.

The full Python suite had separately passed **537 tests in 42.07 seconds** after
the session-cache change. That suite result does not extend the scientific
meaning of the diagnostic sample.
