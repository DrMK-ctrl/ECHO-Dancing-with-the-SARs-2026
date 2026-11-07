# T163 case-to-interface validation

**Update:** This validation report predates the native-grid spatial overlay. Its statement that no spatial comparison was performed describes the earlier assessment. The later overlay, evidence inspector, and updated unresolved assessment are documented in [the spatial-support validation](opera-t163-spatial-support-2026-11-08.md).

## Result

The T163-349925 case loaded its own WGS84 AOI, NASA DSWx-HLS context, and unresolved assessment through its case manifest. In headless Firefox, the live ASF search returned five RTC-S1 features and two repeated-burst candidates on one page. The interface preselected the case's T163-349925-IW2 May 8–June 1 pair, then retrieved the bounded products and masks and rendered the measured comparison on the map.

The rendered comparison reports 1,199/1,199 common-clear cells, VV polarization, and product QA metadata without a consolidated provider PASS/FAIL disposition. Its status stays `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`. The measured log-ratio has mean −2.65 dB and median −1.66 dB. These values describe the OPERA RTC-S1 product pair; they do not establish a physical flood response or cause.

The same browser session flow opened the case's 1,199-cell NASA OPERA DSWx-HLS context and its linked assessment. The HLS products are Sentinel-2A on May 8 and Sentinel-2B on June 2, offset −0.36 and +0.64 days from the corresponding SAR acquisitions. WTR counts change 36→27 on 837 common-valid cells; WTR-2 counts change 135→59 on 1,199 cells. The assessment records its date-anchored CMR screen (`12` metadata candidates) and retrieved optical context. It keeps the water-to-SAR hypothesis `NOT_TESTABLE_WITH_RETAINED_EVIDENCE` because there is no documented common-support pixel-wise comparison and RTC-S1 provider QA is unresolved. The optical map is explicitly context, not SAR validation.

The assessment view also plots the retained SAR and optical acquisition timestamps on one UTC scale. Firefox verified a 24.00-day SAR interval, a 25.00-day optical interval, and optical-minus-SAR offsets of −0.36 and +0.64 days. The display uses the source timestamps and explicitly limits its interpretation to chronology; it does not represent raster alignment or causal support. The timeline markers are positioned through the DOM style API because the application's content security policy disallows inline style attributes. See the [acquisition chronology screenshot](opera-t163-acquisition-chronology-2026-11-08.png), SHA-256 `ac9b5a5ce5826fe21d7f943121918b1e49d8f87165719b99cf91e35737262141`.

A separate Firefox check opened the T024 case and verified that its optional nearest-optical follow-up appears as a third chronology track: SAR 24.00 days, main optical context 25.00 days, and nearest optical context 20.00 days. Its displayed optical-minus-SAR offsets are −2.80 and −1.80 days. This confirms that the shared renderer handles both retained case records and the optional evidence lane; the values remain temporal metadata, not a test of the physical explanation.

The cross-case pair guard was exercised through the browser with live ASF results. After opening the T163 assessment, the UI closed optical context before enabling the mutually exclusive OPERA controls, selected the distinct T024-050661-IW1 May 11–June 4 pair, and returned a diagnostic pair record with no consolidated provider QA verdict. Reopening NASA optical context left the prior assessment closed and displayed a disabled `ASSESSMENT IS FOR A DIFFERENT SAR PAIR` control. The retained assessment's own scene IDs are now the comparison authority once loaded; before loading, the case's nominated pair is used as the early gate. This verified that the T163 assessment cannot be opened beside the different live T024 measurement.

## Reproduction and evidence

Launch the local case from the repository root:

```bash
.venv/bin/echo serve --case-file data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json
```

The case review nominates the T163 pair, but the interface still performs a live ASF catalog query before showing it as a selectable candidate. Choose **OPERA RTC-S1**, search the case date range, and select **Read bounded pair**. Earthdata authentication and the applicable ASF access agreement are required for raster retrieval.

- RTC-S1 diagnostic pair record: [`opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json`](../../data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json), SHA-256 `57fc5735c4e347394816d5d64b6406451ba67b727009b4b94efbd62152dde8ef`.
- NASA CMR metadata screen: [`dswx-hls-screen-T163-349925-2026-11-07.json`](../../data/research/dswx-hls-screen-T163-349925-2026-11-07.json), SHA-256 `b53b9cde1e210488fe0b348be2d69cabd9cd792b1b7f8af5f3df57bb747fe20c`.
- NASA DSWx-HLS bounded evaluation: [`dswx-hls-context-T163-349925-2026-11-07.json`](../../data/research/dswx-hls-context-T163-349925-2026-11-07.json), SHA-256 `93d968429a42d6946f3e3f5a374283f5a8ebe1dee54326a0069bc030e1449b88`.
- Linked assessment: [`opera-rtc-cross-sensor-investigation-T163-349925-2026-11-07.json`](../../data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-07.json), SHA-256 `2cf4d109b00076e107d7ca6d7e31b27771b6b2be613a63eb9d22f72852266fc8`.
- Case-to-raster UI screenshot: [`opera-t163-case-ui-2026-11-08.png`](opera-t163-case-ui-2026-11-08.png), SHA-256 `e7e5f4b1135f878ea3ba8587855d964ec057814eac0a98b59a1c84ea23a16d26`.
- Optical context and assessment screenshot: [`opera-t163-investigation-assessment-2026-11-08.png`](opera-t163-investigation-assessment-2026-11-08.png), SHA-256 `21508499241cb1888483ee5da4977f416349866678090b938155e97084ac3699`.

The application returned the same pair identities and measurements as the retained record. Case-specific endpoints returned this case's optical and assessment records, not the T024 records. The browser confirmed the optical map, catalog-screened follow-up state, evidence record identifier, and diagnostic QA wording.

## Limits

This validation establishes the local software-to-provider workflow for Sentinel-1-derived OPERA RTC-S1 and NASA optical context. It does not establish a QA-cleared NISAR temporal pair, a flood boundary, pixel-wise optical/SAR agreement, physical causation, field truth, or an independently validated event finding. The distinct native grids are not co-registered in this workflow; any common-support comparison requires a documented method and quality review before it can support an interpretation.
