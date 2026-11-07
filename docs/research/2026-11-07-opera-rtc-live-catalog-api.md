# Live OPERA RTC-S1 catalog through ECHO's new API

**Checked:** 2026-11-07 UTC  
**Result:** Catalog integration verified; no raster pixels retrieved

ECHO's new product-specific ASF query was exercised against the Rio Grande do Sul flood search area using WGS84 bounds `(-51.35, -30.12, -51.10, -29.94)` and dates 2024-04-25 through 2024-06-30. The request used the pinned `asf_search` 14.1.0 client, an explicit cap of 250 results, and a single CMR page for the returned set.

The live catalog returned 13 RTC-S1 features on one CMR page. ECHO retained all 13 for the product-specific screen and grouped five 24-day adjacent-date candidates across three Sentinel-1A bursts. Every candidate is metadata-only: the catalog result does not establish pixel-grid equality, common valid coverage, provider QA, or a physical change. Both acquisitions in these five pairs occur after the reported flood onset; these candidates can support a recession/persistence question, not a pre-event versus flood comparison by themselves.

The retained [machine-readable catalog record](../../data/research/opera-rtc-live-catalog-api-2026-11-07.json) includes the exact query, retrieval timestamp, ASF feature records, candidate scene identifiers, source metadata, truncation state, and interpretation limits. This run validates ASF search and pair-screen response handling only. It does not validate the new browser workflow or retrieve measurement assets. The separate product-read attempt remains blocked by ASF's EULA acceptance response, documented in the [OPERA candidate review](2026-11-07-opera-rtc-s1-brazil-flood-candidate.md).

## Follow-up: authenticated bounded pair

Later on 2026-11-07, ASF asset access was rechecked after the Earthdata account's ASF data-access EULA was accepted. Earthdata Login using the configured local netrc authenticated successfully. A single-byte range probe returned HTTP 206 after redirects through ASF Cumulus and Earthdata OAuth, with no authentication or EULA error.

ECHO then read both measurement COGs and per-acquisition masks for the `T024-050660-IW1` Sentinel-1A candidate. The 2024-05-11 and 2024-06-04 observations cover the selected bounded AOI in EPSG:32722. Exact grid agreement and mask checks yielded 1,199 common clear pixel centers. The resulting signed VV gamma-zero log-ratio is retained in the [live pair record](../../data/research/opera-rtc-live-bounded-pair-2026-11-07.json) and remains diagnostic because product-level ASF QA was not retrieved. Browser rendering and source inspection were checked separately using the retained live catalog and pair records; see the [validation report](../validation/opera-rtc-live-pair-2026-11-07.md).

The earlier catalog-only statements above describe that first catalog run and remain accurate for its scope. The follow-up demonstrates live asset access and a real bounded pair calculation; it does not validate an event interpretation or change NISAR QA disposition.
