# NISAR measurement metadata and strict JSON verification

**Date:** 2026-11-13
**Status:** PASS for metadata capture and serialization; source product remains QA-held

## Change

The bounded GCOV reader now retains selected measurement and quality-layer
attributes, including `_FillValue`, `scale_factor`, and `add_offset`. Preview
records hash those attributes and state whether ECHO changed sample values.
The display wording specifies that ECHO applies no *additional* scale or
offset; it does not imply that the source GCOV product is uncalibrated.
Attribute hashes use sorted compact JSON and normalize exactly representable
integer-valued floats to integer tokens. This avoids cross-runtime differences
such as Python's `0.0` versus JavaScript's `0` when reviewers recompute a hash.
Non-finite HDF5 metadata values are serialized as the explicit strings
`"NaN"`, `"Infinity"`, or `"-Infinity"`; they are not emitted as non-standard
JSON numeric tokens. The existing dataset documentation is still needed to
interpret a source `units` value of `"1"`; ECHO's product-level measurement
label remains linear gamma-zero power.

## Live source verification

ECHO's current local interactive server retrieved a bounded HHHH window for
NISAR scene
`NISAR_L2_PR_GCOV_035_072_D_078_4005_DHDH_A_20261110T045757_20261110T045815_P05036_N_P_J_001`
over `[-155.12, 19.7, -155.1, 19.72]` WGS84. The request used 8,454,934
HTTP range bytes and did not download the complete product.

The returned HHHH attributes were `_FillValue="NaN"`,
`description="Covariance between HH and HH"`,
`long_name="Geocoded polarimetric covariance term HHHH"`, `units="1"`, and
`valid_min=0.0`. Their canonical JSON SHA-256 was
`f2d12bb7a3dd77990a252216ed870a8c7b27274e5d183aae6c8f78da876e3652` after
normalizing the integral-valued minimum for cross-runtime reproducibility.
The selected measurement and quality-layer attribute hashes were both
recomputed from the current builder output in Firefox. The combined quality
attribute SHA-256 was
`d71d8272df3f89ba57b5561b95d27e6372a10152bedf3d55d265d291f6dc1702`.
ECHO applied no scale or offset. The provider QA remained `FAIL`, and the
preview disposition remained `QA_HELD_DIAGNOSTIC_PREVIEW`.

The live response was parsed with a strict JSON parser that rejects `NaN` and
other non-standard constants; parsing passed. The existing retained case
record was not rewritten, so its previously registered checksum and retrieval
history remain intact.

## Verification

- `.venv/bin/pytest -q` — **537 passed**.
- `tools/validation/check_gcov_preview_browser.py` against the local interactive
  service — **PASS** for raster rendering, AOI bounds, QA-failure disclosure,
  diagnostic disposition, pixel inspection, and no browser errors. The browser
  test replays the retained preview locally; it makes no provider request.
- A fresh bounded product read and strict-JSON preview record from the current
  builder were replayed through Firefox with the source-attributes requirement
  enabled — **PASS** for
  opening the full record, displaying the attribute hash and sample handling,
  map rendering, and QA/diagnostic disclosure. This browser replay made local
  fixture requests only; the authenticated provider read was the preceding API
  operation.
- The HTTP API response from the preceding live run also passed strict JSON
  parsing. The current verification's provider read used the same bounded
  builder directly; Firefox replay was local and did not make a provider
  request.
- `git diff --check` — passed.

## Current-checkout runtime recheck

The pre-existing interactive service on port 8766 had started before the
measurement-attribute changes. To verify the current backend without
interrupting either existing local service, a temporary server was started on
`127.0.0.1:8767` from this checkout. Python imported `echo` and `echo.web`
directly from the repository's `echo/` directory.

The current service's `/api/gcov-preview` route then read the same bounded Hilo
window: HTTP 200, 8,454,934 range bytes, provider QA `FAIL`, and disposition
`QA_HELD_DIAGNOSTIC_PREVIEW`. The response passed strict JSON parsing and
contained the measurement and quality-attribute hashes listed above. Firefox
replayed that exact response locally and passed all ten checks, including
geolocated raster rendering, pixel inspection, QA-held labeling, source
attribute hash reproduction, visible sample-handling text, and no browser
errors. The replay made only local fixture requests. The temporary service was
stopped afterward; the pre-existing services were left running.

The same current-checkout service passed the T024 challenge-to-map browser
workflow with QA unresolved. The older retained Hilo preview still lacks the
new attribute fields and passes only the compatibility replay. Requiring those
fields for that older record now returns structured failed checks instead of
raising a Python `TypeError`.

## Packed-sample safety follow-up

The bounded HDF5 reader returns stored numeric samples and does not apply
CF-style `scale_factor` or `add_offset` unpacking. The preview builder now
fails closed if either attribute is malformed or non-identity, or if `_Unsigned`
requires integer reinterpretation. This avoids labeling packed integer samples
as linear gamma-zero power or applying the dB display transform to the wrong
values. Identity scale/offset metadata is recorded as provenance and is safe
to retain without changing the samples. Declared finite `_FillValue` samples
are excluded from display-eligible values and from the display stretch, while
remaining present in the checksummed raw source window. NaN fill samples remain
excluded by the finite-value check.

The encoding safeguard follows the [CF Conventions 1.13 packed-data rules](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html#packed-data): when those attributes describe packed values, the application multiplies by `scale_factor` and then adds `add_offset`, while missing-value handling refers to stored values. ECHO currently rejects non-identity encodings instead of claiming to implement that transformation.

The retained current-source NISAR HHHH attributes contain no `scale_factor`,
`add_offset`, or `_Unsigned`, so this guard does not alter that preview. Its
provider QA remains `FAIL` and its disposition remains diagnostic. This change
does not reinterpret or clear provider QA and does not enable temporal analysis.

The focused preview tests passed (**4 passed**) and the complete suite passed
after this follow-up (**540 passed**). A current-checkout Firefox replay on a
temporary loopback service passed all 14 preview checks, including raster/AOI
rendering, pixel inspection, hashed source attributes, visible sample handling,
QA-failure disclosure, request-cache behavior, and no browser errors. The
catalog and preview responses were intercepted and served from retained local
records; the browser run made no external provider request. The temporary
service was stopped after the replay.

A separate Firefox check intercepted the preview request with a local HTTP 422
containing `GCOV scale_factor=2.0 requires packed-sample decoding`. The status
region displayed that reason and “No preview was loaded”; no raster or preview
inspector appeared. This validates the UI failure path only. The 422 was
simulated locally and does not represent a provider response or the retained
NISAR scene's metadata.
