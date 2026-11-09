# Expose product method scope with source records

## Decision

When a user inspects an evidence record, show a concise, source-linked guide to the product's measurement domain, ECHO paths, applicability requirements, and interpretation limits. Keep this guide separate from the raw evidence record and from acquisition-specific QA and analysis results.

Register profiles only for product families that ECHO already reads or uses: NISAR L2 GCOV, NISAR L2 GUNW, OPERA RTC-S1, and OPERA DSWx-HLS. Unknown record types receive no inferred profile. The endpoint is read-only and explicitly states that a product guide does not assess the linked acquisition's QA, suitability, or conclusions.

## Rationale

ECHO's product semantics and implemented analysis paths were previously distributed across readers, validators, and case-specific explanations. A small source inspector makes those boundaries visible at the point where a user inspects evidence, without turning a product-family description into a scene-level acceptance decision.

Profiles keep scientifically different data distinct: GCOV backscatter/covariance, GUNW interferometric phase and coherence, Sentinel-1-derived RTC-S1 power, and optical DSWx-HLS water classification. They state requirements and unsupported interpretations, but do not calculate compatibility, QA, or findings.

## Verification and limits

- Unit and endpoint coverage verifies registered profiles, copied return values, conservative handling of unknown products, and request validation.
- A headless Firefox walkthrough opened the T163 RTC-S1 pair evidence record. The inspector displayed its Sentinel-1 origin, diagnostic method, requirements, and limitations; the raw source record remained present. At a 1366 px viewport, document width matched viewport width.
- `.venv/bin/python -m pytest -q` passed: **423 passed**.
- The profile text is a curated product-level guide with links to official product documentation. It is not generated from a particular granule's metadata and does not replace provider documentation, product QA, or analysis manifests.

## References

- [ASF NISAR GCOV product documentation](https://nisar-docs.asf.alaska.edu/data-products/level-2/gcov/)
- [ASF NISAR GUNW product documentation](https://nisar-docs.asf.alaska.edu/data-products/level-2/gunw/)
- [ASF HyP3 OPERA RTC-S1 product guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/)
- [NASA OPERA DSWx-HLS product documentation](https://www.jpl.nasa.gov/go/opera/products/)
