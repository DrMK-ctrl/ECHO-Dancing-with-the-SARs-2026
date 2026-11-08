# Show GCOV maturity separately from provider QA

**Date:** 2026-11-08
**Status:** Implemented; automated suite passed

## Decision

Carry the GCOV collection's product maturity into each pair source record and show it beside provider-QA status wherever a descriptive pair result is presented. Use `BETA`, `PROVISIONAL`, or `VALIDATED` only for the recognized ASF collection names; otherwise preserve `UNKNOWN` in the record and show `MATURITY UNSPECIFIED`. Label pairs with differing supported maturities `MIXED MATURITY`.

## Rationale

Provider QA and product maturity answer different questions. A passing provider QA report does not make a provisional product validated, while a product's collection maturity does not establish that its individual QA checks passed. Showing both in the map caption, map attribution, warning, and source inspector makes that distinction visible during review.

## Verification and limits

- Regression tests cover QA-held provisional products, QA-passing BETA products held before pixel reads, and a provisional pair that reaches descriptive measurement.
- The full Python suite passed: **300 tests**.
- Headless Firefox loaded the local ECHO dashboard. A controlled successful-pair display state was not confirmed in the browser harness; the success-state wording is therefore covered by code review and backend tests, not claimed as browser-verified.
- No real NISAR pair was processed or reclassified by this presentation change. Current retained NISAR observations remain subject to their recorded provider-QA dispositions.
