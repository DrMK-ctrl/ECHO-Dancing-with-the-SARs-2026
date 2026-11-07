# Live OPERA RTC-S1 catalog through ECHO's new API

**Checked:** 2026-11-07 UTC  
**Result:** Catalog integration verified; no raster pixels retrieved

ECHO's new product-specific ASF query was exercised against the Rio Grande do Sul flood search area using WGS84 bounds `(-51.35, -30.12, -51.10, -29.94)` and dates 2024-04-25 through 2024-06-30. The request used the pinned `asf_search` 14.1.0 client, an explicit cap of 250 results, and a single CMR page for the returned set.

The live catalog returned 13 RTC-S1 features on one CMR page. ECHO retained all 13 for the product-specific screen and grouped five 24-day adjacent-date candidates across three Sentinel-1A bursts. Every candidate is metadata-only: the catalog result does not establish pixel-grid equality, common valid coverage, provider QA, or a physical change. Both acquisitions in these five pairs occur after the reported flood onset; these candidates can support a recession/persistence question, not a pre-event versus flood comparison by themselves.

The retained [machine-readable catalog record](../../data/research/opera-rtc-live-catalog-api-2026-11-07.json) includes the exact query, retrieval timestamp, ASF feature records, candidate scene identifiers, source metadata, truncation state, and interpretation limits. This run validates ASF search and pair-screen response handling only. It does not validate the new browser workflow or retrieve measurement assets. The separate product-read attempt remains blocked by ASF's EULA acceptance response, documented in the [OPERA candidate review](2026-11-07-opera-rtc-s1-brazil-flood-candidate.md).

Next: connect the provider-specific catalog and pair controls to the geographic workspace, then retry a bounded read after ASF asset authorization is complete. Preserve `provider_qa=NOT_RETRIEVED` unless a documented, product-specific QA source is added; a successful masked log-ratio computation remains diagnostic until that quality status and the scene compatibility are evaluated.
