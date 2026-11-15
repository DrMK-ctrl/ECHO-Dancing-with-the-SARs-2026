# T163 spatial overlay reproduction against retained records

**Checked:** 2026-11-13 12:17 UTC
**Disposition:** Original WTR summaries reproduce; current evaluator adds WTR-2 analyses. Diagnostic status is unchanged.

## Inputs and reproduction

The current spatial-support evaluator was run against the retained T163 OPERA RTC-S1 pair and DSWx-HLS context. Its output was written to `/tmp/echo-t163-spatial-recomputed.json`; the core assessment builder was then run with that output and the retained catalog screen, writing to `/tmp/echo-t163-investigation-rebuilt.json`. No repository evidence record was overwritten.

```bash
.venv/bin/python tools/research/evaluate_rtc_dswx_spatial_support.py \
  --pair data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --output /tmp/echo-t163-spatial-recomputed.json

.venv/bin/python tools/research/build_cross_sensor_investigation.py \
  --sar-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical-record data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --catalog-screen-record data/research/dswx-hls-screen-T163-349925-2026-11-07.json \
  --spatial-support-record /tmp/echo-t163-spatial-recomputed.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output /tmp/echo-t163-investigation-rebuilt.json
```

## Results

The recomputed overlay and retained schema-v1 record both contain 1,254 SAR-grid cells, 1,199 SAR-valid cells, 1,199 retained DSWx cells, and 1,043 cells with any common-valid WTR area. Each source-recorded WTR support threshold also reproduced exactly:

| Minimum common-valid WTR area | Cells | Increase > 0.05 | Decrease < −0.05 | Change within ±0.05 | Median SAR log-ratio |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50% | 826 | 15 | 20 | 791 | −1.316 dB |
| 75% | 738 | 14 | 14 | 710 | −1.215 dB |
| 90% | 738 | 14 | 14 | 710 | −1.215 dB |
| 95% | 738 | 14 | 14 | 710 | −1.215 dB |

The current evaluator emits schema v2 and adds WTR-2, cloud-clear, and mask-sensitivity fields that are absent from the retained schema-v1 record. Therefore the full JSON objects and checksums are expected to differ even though the original WTR summary metrics above match. The temporary assessment rebuild returned `CAUSAL_INTERPRETATION_UNRESOLVED`, with physical cause `UNRESOLVED`, event extent `NOT_ESTABLISHED`, and `nisar_measurement_present: false`.

## Integrity and limits

Input and tool SHA-256 values at reproduction time:

- SAR pair: `41e040338b4726766a8e1724e74bac2f211cd71a07190f66711b04a4843603cf`
- Optical context: `93d968429a42d6946f3e3f5a374283f5a8ebe1dee54326a0069bc030e1449b88`
- Retained schema-v1 spatial record: `ff2dc782bebb40c489d963324e8ab7a32fef7d36b81a55c4d5fcf3ddfebc8def`
- Current overlay evaluator: `4f148f32ccccc67fafc9898997b11aeb8a9f69dc253ea612812ece9bdd928aec`
- Current assessment builder: `8dd5342c2c7dfd809414885238ada575be9fe4a5380a30117a686f81195c1781`

The assessment rebuild used only the SAR pair, optical context, catalog screen, and recomputed spatial overlay. It did not reproduce the full active assessment with its additional polarization, temporal, rainfall, and other evidence records. This check verifies the stated WTR overlay calculations and the core builder's unresolved disposition; it does not re-read provider pixels, validate product QA, or establish a cause, flood extent, or superiority over conventional change detection. The OPERA pair remains diagnostic.
