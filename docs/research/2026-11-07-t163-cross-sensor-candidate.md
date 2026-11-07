# T163 cross-sensor candidate review

## Decision

Retain the Sentinel-1A OPERA RTC-S1 T163-349925-IW2 May 8–June 1 pair as a stronger diagnostic candidate for a future integrated case walkthrough. It has complete common-clear coverage of the bounded AOI and closely timed NASA OPERA DSWx-HLS context. It does not replace the current T024 interface case or qualify as a validated physical-change result.

## Evidence

- RTC-S1 source record: [`opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json`](../../data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json)
- Failed adjacent-burst comparison retained for audit: [`opera-rtc-live-pair-T163-349924-IW2-2024-11-07.json`](../../data/research/opera-rtc-live-pair-T163-349924-IW2-2024-11-07.json)
- Pre-event metadata search over January 1–May 10: [`opera-rtc-s1-brazil-flood-full-pre-event-screen-2026-11-07.json`](../../data/research/opera-rtc-s1-brazil-flood-full-pre-event-screen-2026-11-07.json)
- NASA CMR DSWx-HLS search anchored to the T163 acquisition times: [`dswx-hls-screen-T163-349925-2026-11-07.json`](../../data/research/dswx-hls-screen-T163-349925-2026-11-07.json)
- Bounded DSWx-HLS pixel and quality evaluation: [`dswx-hls-context-T163-349925-2026-11-07.json`](../../data/research/dswx-hls-context-T163-349925-2026-11-07.json)

The two RTC-S1 acquisitions are May 8 and June 1, 2024, on the same burst identifier and Sentinel-1A. Their retained log-ratio has 1,199 of 1,199 AOI centers in the common-clear mask (mean −2.65 dB, median −1.66 dB). The product record remains `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`: both products have QA metadata, but neither has a consolidated provider PASS/FAIL disposition.

The NASA DSWx-HLS products are OPERA granules acquired May 8 (Sentinel-2A) and June 2 (Sentinel-2B), about 0.36 days before and 0.64 days after the corresponding RTC-S1 acquisitions. The June 2 Sentinel-2 granule was the second-nearest CMR result after a June 2 Landsat 8 granule; Sentinel-2 was retained to keep the optical pair on one sensor family. Over the same WGS84 AOI, WTR has 837 common-valid cells and water-class counts 36→27; WTR-2 has 1,199 common-valid cells and counts 135→59. These are classifications from NASA's optical HLS-derived product, not field truth or SAR validation.

## Limits and next step

The records do not establish pixel-wise cross-sensor correspondence: the products use different native grids, and the extraction does not perform a common-support spatial comparison. The class-count trend is descriptive and cannot explain the aggregate radar response. The SAR products remain diagnostic pending an authoritative QA disposition. An adjacent same-track product pair, T163-349924-IW2, returned zero common-clear AOI centers; it is unsuitable for this AOI. The wider January–May 10 catalog screen returned only the May 8 burst family and no earlier same-burst pre-event scene, so this pair cannot establish a pre-onset SAR baseline.

The efficient next integration step is to make the interface load an explicit case record that links this measured pair, its closely timed optical context, and the existing hypothesis/evidence schema. Keep the existing T024 case available until the T163 case is verified through the same map and evidence-inspection path. A later common-support spatial analysis would require a documented grid/area-overlap method and fresh quality review; it must not be inferred from matching AOI bounds or nearest-neighbor samples.
