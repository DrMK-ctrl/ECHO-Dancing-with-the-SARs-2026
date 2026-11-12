# Upstream status of the GCOV identification QA failure — 2026-11-12

## Finding

The reviewed NISAR GCOV candidates remain provider-QA `FAIL`. ECHO's retained product-specific reports identify the recurring failure as the aggregate identification-group check, including `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`. These exact product results remain the controlling disposition; passing raster checks and ECHO's bounded diagnostic previews do not clear them.

An upstream ISCE3 issue documents a GCOV QA report containing the same `(NOT SPECIFIED)` observation-mode value, alongside other metadata checks. The linked `nisarqa` pull request that proposes general checks for placeholder strings, string dtypes, and attribute dtypes is still open and awaiting review. This is corroborating context, not evidence that the issue has been fixed, that the reviewed ECHO products are the same products in the issue, or that ASF has accepted a correction.

ASF's current VALIDATED known-issues page lists the resolved incomplete-L0B issue and a permanent acquisition gap; it does not list this identification-group failure. The PROVISIONAL known-issues page was not accessible during this review. Absence from the VALIDATED page is not confirmation that ASF has no internal investigation or that the product metadata are acceptable.

## Engineering disposition

- Keep every affected product at provider-QA `FAIL` / QA-held; do not infer eligibility from local metadata inspection or raster-level checks.
- Do not repeat QA downloads or pixel comparison for the same unchanged products. Reopen only if ASF publishes a corrected/replacement product, changes the canonical QA report, or provides product-specific guidance.
- The next useful external evidence is an ASF/NASA response that identifies whether these exact product identifiers are affected by a known metadata-generation defect and whether a correction or replacement is planned. No inquiry was sent as part of this review.
- ECHO's QA-gated analysis, real-data diagnostic preview, and local read-only demonstration remain unaffected by this upstream status.

## Sources reviewed

- [ASF NISAR VALIDATED known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/)
- [ISCE3 issue #216: GCOV dataset and attribute issues](https://github.com/isce-framework/isce3/issues/216)
- [nisarqa pull request #155: general attribute and placeholder validation](https://github.com/isce-framework/nisarqa/pull/155)
- [Existing P05036 candidate-specific QA review](2026-11-11-p05036-gcov-qa-root-cause.md)

This record summarizes public upstream status observed on 2026-11-12. Recheck the issue, pull request, and ASF guidance before changing the product disposition.
