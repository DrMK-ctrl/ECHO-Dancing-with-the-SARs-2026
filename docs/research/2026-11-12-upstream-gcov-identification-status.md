# Upstream status of the GCOV identification QA failure — 2026-11-12

## Finding

The reviewed NISAR GCOV candidates remain provider-QA `FAIL`. ECHO's retained product-specific reports identify the recurring failure as the aggregate identification-group check, including `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`. These exact product results remain the controlling disposition; passing raster checks and ECHO's bounded diagnostic previews do not clear them.

The four retained P05036 report sets consistently identify product specification `1.6.0`, product software `0.25.21`, and QA software `17.2.0`. NASA's publicly linked GCOV Product Specification Rev F is version `1.5.0`, so it is not the exact specification revision named by these products. That public document describes `instrumentName` generically as the instrument name and `listOfObservationModes` as a list of modes used to generate the input RSLC; it does not enumerate acceptable `instrumentName` strings. By contrast, the corresponding `nisarqa` v17.2.0 implementation explicitly accepts `L-SAR` or `S-SAR` and rejects placeholder observation-mode values. Thus the validator's reason for failing these fields is reproducible from its source, while the public PDF alone does not settle whether the products violate the full 1.6.0 product contract.

An upstream ISCE3 issue documents a GCOV QA report containing the same `(NOT SPECIFIED)` observation-mode value, alongside other metadata checks. The linked `nisarqa` pull request that proposes general checks for placeholder strings, string dtypes, and attribute dtypes is still open and awaiting review. This is corroborating context, not evidence that the issue has been fixed, that the reviewed ECHO products are the same products in the issue, or that ASF has accepted a correction.

The current `nisarqa` releases page labels `R05.03.1` as latest and links it to tag `v17.2.0`; the reviewed P05036 reports already used `17.2.0`. The software-release route therefore has no later published version to try as a correction. The `nisarqa` v17.2.0 release notes say it added the product-spec XMLs for v1.6.0, matching the `productSpecificationVersion` captured in the P05036 reports.

ASF's current VALIDATED known-issues page lists the resolved incomplete-L0B issue and a permanent acquisition gap; it does not list this identification-group failure. The PROVISIONAL known-issues page was not accessible during this review. Absence from the VALIDATED page is not confirmation that ASF has no internal investigation or that the product metadata are acceptable.

## Engineering disposition

- Keep every affected product at provider-QA `FAIL` / QA-held; do not infer eligibility from local metadata inspection or raster-level checks.
- Do not repeat QA downloads or pixel comparison for the same unchanged products. Reopen only if ASF publishes a corrected/replacement product, changes the canonical QA report, or provides product-specific guidance.
- The next useful external evidence is an ASF/NASA response that identifies whether these exact product identifiers are affected by a known metadata-generation defect and whether a correction or replacement is planned. No inquiry was sent as part of this review.
- ECHO's QA-gated analysis, real-data diagnostic preview, and local read-only demonstration remain unaffected by this upstream status.

## Sources reviewed

- [ASF NISAR VALIDATED known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/)
- [`nisarqa` releases](https://github.com/isce-framework/nisarqa/releases) (`R05.03.1`, latest, points to v17.2.0)
- [NASA SDS L2 GCOV Product Specification, Rev F, v1.5.0](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf) (public specification is older than the `1.6.0` recorded in the reviewed products; downloaded copy SHA-256: `bfddc039eab7ad328f63e8425fa8f0e0b10f9ee339983c918b13b9f6d57d89a2`)
- [`nisarqa` v17.2.0 GCOV product schema](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/product_specs/1.6.0/nisar_L2_GCOV.xml)
- [`nisarqa` v17.2.0 identification checks](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py)
- [ISCE3 issue #216: GCOV dataset and attribute issues](https://github.com/isce-framework/isce3/issues/216)
- [nisarqa pull request #155: general attribute and placeholder validation](https://github.com/isce-framework/nisarqa/pull/155)
- [Existing P05036 candidate-specific QA review](2026-11-11-p05036-gcov-qa-root-cause.md)

This record summarizes public upstream status observed on 2026-11-12. Recheck the issue, pull request, and ASF guidance before changing the product disposition.

## Live source recheck — 2026-11-12

The [`nisarqa` placeholder-validation PR #155](https://github.com/isce-framework/nisarqa/pull/155) remains open and awaits requested code-owner reviews. ASF's current VALIDATED known-issues page lists incomplete L0B products as resolved with CRID P05036 and the permanent July/August data gap; it does not list the observed identification-group QA failures. ASF's PROVISIONAL known-issues page (updated July 30, 2026) describes other P05023 limitations and advises caution across maturities. Neither page establishes an ASF disposition for the exact identification metadata in ECHO's sampled products; their absence is not evidence that ASF has no internal investigation. The provider QA `FAIL` remains controlling.
