# On-demand provider QA inspection validation

**Date:** 2026-11-07

**Result:** Selected-scene endpoint and browser inspection verified; no raster processing performed

## Automated checks

The web endpoint tests verify that a supported ASF product request returns a serialized parsed QA record with its source hash, provider check rows, and retrieval metadata. A forged third-party product host is rejected before the retrieval function is called, oversized QA requests are rejected before retrieval, and the JSON attachment endpoint requires its catalog product and QA summary to identify the same supported ASF scene. The focused web suite passed (11 tests); the full suite passed (96 tests), Python compile checks passed, and `git diff --check` was clean.

## Live browser and provider retrieval

Ran the local interface against the retained Kathmandu AOI catalog response in headless Firefox and selected scene `NISAR_L2_PR_GCOV_028_048_D_074_4005_DHDH_A_20260816T125812_20260816T125846_P05023_N_F_J_001`. The **FETCH QA** action showed a retrieval-in-progress state and then fetched the canonical ASF CSV using the configured local Earthdata Login. All nine provider check rows were rendered, along with the original ASF URI, retrieval details, size (1,441 bytes), and SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`. The provider disposition was `FAIL`; the identification-group check was `FAIL` and the other reported checks were `PASS`.

The acquisition details changed to `QA SUMMARY · FAIL`. The panel stated that this request did not re-read HDF5 identification metadata or radar arrays. The serialized source record identifies the Alaska Satellite Facility DAAC, HTTPS byte-range retrieval, and the exact QA summary artifact URI. This is a provider quality record, not an ECHO measurement or a provider disposition of scientific usability.

Choosing **EXPORT SOURCE RECORD** downloaded a 25,294-byte JSON attachment in Firefox. Its catalog-feature scene ID matched the QA-summary scene ID, the catalog maturity was PROVISIONAL, the provider status remained FAIL, and its summary SHA-256 matched the displayed artifact hash. The export included all three interpretation limits and the source query. The test download was removed after inspection; the reproducible export behavior is retained in the app and its endpoint tests, while per-session exports are not automatically added to the repository.

## Limits

This validation retrieved and parsed one QA CSV only. It did not retrieve product HDF5 metadata or measurement arrays, establish valid-pixel AOI coverage, align grids, run a change measurement, or clear the scene's QA hold. Browser-session results are not persisted as case evidence; the source URI, timestamp, retrieval metadata, and checksum are available in the session's machine-readable inspector and can be recorded in a later reproducible case-screen artifact if needed.
