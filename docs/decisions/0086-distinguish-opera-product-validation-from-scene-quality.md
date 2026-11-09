# Decision 0086: Distinguish OPERA product validation from scene quality

**Date:** 2026-11-09
**Status:** Implemented and validated for the retained T024 series

## Context

ECHO's retained OPERA RTC-S1 pair and series records say that the ASF sidecars contain per-product QA metadata but no consolidated per-scene `PASS` or `FAIL`. The current analysis therefore remains diagnostic. That is a truthful statement about the sidecars, but it can be misread as though NASA had not validated the product or as though the scenes had failed provider QA.

The primary documentation makes a more specific distinction:

- JPL identifies RTC-S1 as a Level-2 NASA OPERA product and publishes accuracy results for its validation data. The reported requirements are absolute and relative geolocation error below 6 m for 80% of validation data, and terrain-flattening difference below 1 dB for 80%; JPL reports that 100% of the validation data considered met each requirement. Those are validation-sample results, not a certificate for an individual acquisition or AOI.
- The RTC-S1 product specification defines scene metadata for geolocation accuracy and RFI. It says RFI information is included when RFI is detected and the input annotation information is available. RFI metadata and a mitigation descriptor therefore need to be surfaced as observations, not translated into a pass or failure.
- ASF documents the per-acquisition RTC validity mask: code 0 is valid and unaffected by layover or shadow; codes 1–3 remain valid with shadow and/or layover; 255 is invalid. The specific product mask should be used for its acquisition.

## Decision

Keep the existing provider state `PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION` and the current diagnostic scientific status. Do not synthesize a provider verdict from product-level validation, masks, or ECHO's own numerical checks.

Record three separate layers in the temporal-series source record and interface:

1. **Provider product validation:** the JPL validation scope and published validation-sample results, with a clear statement that they do not certify the selected scene or AOI.
2. **Per-acquisition quality metadata:** the exact sidecar values and missing fields, including the fact that the retained T024 acquisitions report RFI information and mitigation. Do not infer that mitigation removed all effects.
3. **ECHO bounded measurement checks:** the exact product masks, finite positive measurements, same burst/platform/product version, grid registration, selected AOI support, and common support. Report measured results and excluded-cell counts without turning this local screen into provider QA.

The retained OPERA comparison stays diagnostic after this review. A backscatter comparison alone must not establish a physical cause, event boundary, damage, or ground condition. Any relationship to a physical explanation still requires evidence appropriate to that explanation and explicit treatment of the RFI limitation.

## Evidence inspected

- T024 three-date series: [`opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json`](../../data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json). Its all-date common support is 1,034 of 1,199 selected AOI centers. The three per-product sidecars include geolocation values and RFI reports; each says RFI information is available and records `BasedOnNoiseMeas` mitigation in the time and frequency domains. The RFI report is not a per-pixel residual-effect layer.
- Existing validation record: [T024 temporal series validation](../validation/opera-t024-temporal-series-2026-11-08.md), including exact grid checks, per-product masks, hashes, and current diagnostic disposition.
- JPL RTC-S1 product and validation summary: <https://www.jpl.nasa.gov/go/opera/products/rtc-product/>.
- JPL OPERA RTC-S1 Product Specification v1.0.3: <https://d2pn8kiwq2w21t.cloudfront.net/documents/ProductSpec_RTC-S1.pdf>.
- ASF OPERA RTC-S1 Product Guide, including mask codes and per-acquisition mask guidance: <https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/>.
- OPERA-Cal-Val validation tools and validation-plan reference: <https://github.com/OPERA-Cal-Val/calval-RTC>.

## Consequence

The absence of an aggregate sidecar verdict is neither evidence of a failed scene nor permission to call it cleared. The T024 series now carries a reproducible review and exposes it in the temporal-series inspector. The review preserves provider, per-acquisition, and ECHO-local checks as distinct records; the actual OPERA measurements continue to exercise the map and investigation workflow while the status remains diagnostic. NISAR QA requirements are unaffected. See [scoped quality-review validation](../validation/opera-t024-scoped-quality-review-2026-11-09.md).
