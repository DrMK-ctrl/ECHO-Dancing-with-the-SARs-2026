# T163 DSWx-HLS WTR-2 mask sensitivity

**Disposition:** Diagnostic optical context only. The linked Sentinel-1/OPERA RTC-S1 pair remains diagnostic; the physical cause and event extent remain unresolved.

## Question and method

The retained T163 AOI context contains native-grid WTR, WTR-2, and CLOUD samples for both DSWx-HLS dates. This evaluation asks whether the WTR-2 water-class comparison changes when observations flagged by the product's cloud, shadow, or snow mask are excluded. It does not interpret WTR-2 as a SAR measurement or as ground truth.

The evaluator intersects the retained DSWx-HLS cell polygons with the RTC-S1 cell polygons in the RTC-S1 projected CRS and weights class fractions by exact intersection area. It does not resample either product. WTR-2 summaries use valid class codes 0, 1, and 2 on both dates. The clear-mask sensitivity additionally retains only cells with CLOUD class 0 or 8 on both dates, following the [NASA/JPL OPERA DSWx-HLS product specification](https://d2pn8kiwq2w21t.cloudfront.net/documents/OPERA_DSWx-HLS_ProductSpec_v1.0.0_D-107395_RevB.pdf). The source product is [NASA OPERA DSWx-HLS Version 1](https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-HLS_V1), DOI `10.5067/OPDSW-PL3V1`.

## Retained-data result

Of 1,199 serialized optical samples, 837 have CLOUD classes 0/8 at both dates. On those 837 samples, WTR and WTR-2 have the same 0/1/2 transition matrix and both count water-coded classes from 36 before to 27 after. The unfiltered WTR-2 product summaries separately report 135 to 59; those counts include different cloud/snow-flagged support and should not be read as an independently established water change.

At a minimum 75% optical-area coverage threshold:

| Support | SAR cells | Cells with absolute water-fraction shift >0.05 | Descriptive Pearson r with signed SAR ratio |
|---|---:|---:|---:|
| Existing WTR valid-class support | 738 | 28 (14 up, 14 down) | −0.108 |
| WTR-2 without CLOUD filtering | 1,166 | 141 (15 up, 126 down) | −0.013 |
| WTR-2 with common CLOUD 0/8 support | 738 | 28 (14 up, 14 down) | −0.108 |

The unfiltered summary includes 428 additional SAR cells that do not meet the clear-mask 75% area threshold. Those cells contain 113 larger shifts (1 increase and 112 decreases). On the same 738 clear-supported SAR cells, unfiltered and clear-filtered WTR-2 both show 28 larger shifts; none of their per-cell changes differ by more than 0.05. The total-count contrast therefore comes from the additional lower-clear-support cohort, while the matched cohort shows no per-cell WTR-2 difference above the stated 0.05 threshold.

These are descriptive, spatially dependent cells; no inferential statistics are reported. The result does not validate RTC-S1, establish flood extent or causality, or convert optical classes into ground truth. The T163 SAR pair remains diagnostic because its provider metadata have no consolidated QA disposition.

## Integration and reproduction

The new versioned spatial record is linked from the active T163 case assessment. The assessment preserves its unresolved causal disposition and records the mask sensitivity under the spatial-association follow-up. The prior overlay and assessment files remain available as historical records. The interface displays both support-specific counts and the matched-cohort comparison, with an evidence-inspection link to the complete cell-level record.

Recompute the spatial overlay from the retained source records:

```bash
.venv/bin/python tools/research/evaluate_rtc_dswx_spatial_support.py \
  --pair data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --output /tmp/echo-t163-wtr2-mask-sensitivity.json
```

The output records SHA-256 values for the SAR pair, optical context record, each WTR/WTR-2/CLOUD source raster, and the processing script. The versioned retained output is [`opera-rtc-dswx-spatial-support-T163-349925-VV-mask-sensitivity-2026-11-09.json`](../../data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-mask-sensitivity-2026-11-09.json); the active linked assessment is [`opera-rtc-cross-sensor-investigation-T163-349925-2026-11-09-mask-sensitivity.json`](../../data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-09-mask-sensitivity.json).

## Retained artifact checksums

- Spatial sensitivity record: `131f1f87b6d0be4c15aab17e1a8ab155eced88243e9d43eb36df968aad698f79`
- Updated polarization sensitivity record: `da3fcd9816374bcf8e0cb0442d0271773d79767c7a5ab70aea68a9369b108754`
- Active T163 assessment snapshot: `d54aefa9979a976b2feb78841647fb9700c2fb2fce892e0036b1b7e979b009a9`
- Spatial evaluator: `4f148f32ccccc67fafc9898997b11aeb8a9f69dc253ea612812ece9bdd928aec`
- Cross-sensor assessment builder: `8dd5342c2c7dfd809414885238ada575be9fe4a5380a30117a686f81195c1781`

Software verification includes synthetic geometry and mask-gating cases, an integration test against the retained T163 source records, and the linked assessment/evidence API tests. The full suite passed: `437 passed`. A headless Firefox session opened the active T163 assessment, displayed the new mask-sensitivity text, and opened **Inspect cell-level evidence**; the dialog parsed the checksum-linked diagnostic record with 1,254 SAR cells, CLOUD codes `[0, 8]`, and the 738-cell matched cohort. These checks validate implementation and record linkage, not the scientific QA status of the underlying SAR pair.
