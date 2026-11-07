# Decision 0019: hold pre-calibration GCOV from paired measurement

**Date:** 2026-11-07  
**Status:** Implemented and unit-tested

## Context

ECHO supports BETA, PROVISIONAL, and VALIDATED GCOV catalog discovery and allows diagnostic previews when provider QA fails. The paired measurement path previously treated a provider QA `PASS` as sufficient to proceed for any allowlisted collection. ASF's NISAR User Guide says BETA products were not fully calibrated and documents a misaligned valid-data mask that propagates to higher-level products, including GCOV. A passing summary alone cannot clear this known product-maturity limitation.

## Decision

- Retain BETA catalog discovery and single-scene diagnostic preview.
- Permit quantitative paired GCOV analysis only for `NISAR_L2_GCOV_PROVISIONAL_V1` and `NISAR_L2_GCOV_V1`.
- If both BETA products report provider QA `PASS`, return `MATURITY_HELD` with the QA evidence preserved. Do not inspect product identification metadata or read radar arrays.
- Keep a second maturity check inside the low-level analyzer so direct callers cannot bypass the restriction.
- Reconsider BETA analysis only after a product-specific correction for the documented mask issue is independently justified and validated.

## Verification and limits

- A synthetic QA-PASS BETA pair returns `MATURITY_HELD`; test doubles assert product metadata and radar arrays are not read.
- The low-level analysis function rejects BETA windows even when supplied passing QA evidence.
- A headless Firefox interaction using a temporary BETA catalog copy and a mocked QA-PASS `MATURITY_HELD` response displayed the separate product-maturity inspector, map caption, `NOT_READ` and `NOT_PERFORMED` gates, and no measurement layer.
- The browser check used a mocked response and did not retrieve or process a BETA product. It verifies interface presentation only; backend gate tests provide the decision-path evidence. No real BETA QA-PASS product, pixel read, comparison, or scientific result is asserted.
- Tests verify software behavior. No BETA provider product has passed QA in the retained live samples, and no BETA comparison or correction is asserted.

## Reference

- ASF, [Pre-Calibration Sample Products: known issues](https://nisar-docs.asf.alaska.edu/product-known-issues/), updated 2026-02-27. ASF states that BETA products were not fully calibrated, describes valid-data mask misalignment, and identifies fully calibrated PROVISIONAL products as available from July 2026.
