# Decision 0084: retry transient GCOV range transport failures within one budget

Date: 2026-11-09

## Context

One authenticated, bounded read of an Iraq PROVISIONAL GCOV scene failed with an `aiohttp.ClientOSError` while HDF5 requested HTTPS byte ranges. The initial-byte request succeeded, and a second read with a 16 KiB read-ahead block returned a real measurement window. A later read through ECHO's unchanged 128 KiB path also succeeded, so the incident does not establish a persistent service restriction or a generally better block size.

## Decision

Keep 128 KiB as the primary read-ahead size. In the single-observation preview path only, retry once at 16 KiB when the reader reports a recognized transport connection failure or timeout. Do not retry authentication errors, malformed products, absent datasets, provider QA failures, or range-budget errors. Carry the bytes consumed by the failed first attempt into the retry, limiting combined requested ranges to the existing 64 MiB ceiling. Retain both attempt outcomes in the preview access record and surface the retry in the source inspector.

## Evidence and verification

The same P05023 scene and 0.02° AOI have been read through the real preview path at both 16 KiB and the default 128 KiB settings. A live `POST /api/gcov-preview` returned HTTP 200 using the default 128 KiB path, with a 113 × 92 source window, 9,918 AOI centers, and 7,351,192 requested range bytes. Its canonical ASF QA summary remains `FAIL`; the output remains `QA_HELD_DIAGNOSTIC_PREVIEW`. The fallback was exercised with a simulated connection reset, verifying error classification, the reduced remaining budget, the combined byte count, and unchanged QA disposition. The live API read succeeded on its primary attempt, so automatic fallback has not yet been observed against a live transport failure. See the [preview evidence](../validation/nisar-iraq-gcov-preview-2026-11-08.md).

## Limits

This is a one-retry resilience measure, not a performance optimization or proof that smaller blocks fix the provider reset. It applies only to the single-observation preview reader. Retry behavior and the HTTP preview path are covered by Python tests, and the modified source inspector passes a GJS JavaScript parse check. The interface was not visually verified in a browser. No temporal analysis or QA override is introduced.
