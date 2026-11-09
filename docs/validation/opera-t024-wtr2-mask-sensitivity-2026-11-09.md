# T024 WTR-2 mask sensitivity on retained RTC-S1 observations

Date: 2026-11-09

Disposition: reproducible diagnostic overlay; causal interpretation unresolved

## Scope

The generalized native-grid, area-weighted overlay was applied to the retained T024-050661 OPERA RTC-S1 pair acquired on 2024-05-11 and 2024-06-04. It uses the same retained DSWx-HLS observation record as the T024 case (2024-05-08 and 2024-06-02), so the optical context is close in time to the SAR dates but is also shared with the other Rio Grande do Sul case. This is a second SAR-pair sensitivity check, not independent event confirmation.

RTC-S1 provider metadata contain no consolidated QA disposition. The resulting association remains diagnostic. DSWx-HLS is optical algorithm output, not field truth or validation of the SAR response. No resampling or inferential statistic is used.

## Results at 75% common area support

- Unmasked WTR-2: 1,042 SAR cells; water fraction increased by more than 0.05 in 13 and decreased by more than 0.05 in 121.
- WTR-2 restricted to CLOUD classes 0 or 8 at both dates: 637 SAR cells; 12 increased and 14 decreased by more than 0.05.
- On the identical 637-cell clear-supported cohort, unmasked and cloud-clear WTR-2 comparisons differed by more than 0.05 in zero cells.
- The 405 additional cells available only without the CLOUD restriction included one increase and 107 decreases greater than 0.05.

The smaller clear-supported cohort therefore removes most cells responsible for the broad unmasked change count, while the paired values agree within the declared 0.05 threshold on the shared clear-supported cohort. This is a mask/support sensitivity result, not evidence that cloud effects caused the SAR response. The corresponding clear-supported descriptive correlation is −0.056 and no inferential interpretation is made.

## Reproduction and evidence

The machine-readable overlay is [`opera-rtc-dswx-spatial-support-T024-050661-mask-sensitivity-2026-11-09.json`](../../data/research/opera-rtc-dswx-spatial-support-T024-050661-mask-sensitivity-2026-11-09.json). The active T024 assessment links that record and retains its source checksums at [`opera-rtc-cross-sensor-investigation-T024-050661-2026-11-09-mask-sensitivity.json`](../../data/research/opera-rtc-cross-sensor-investigation-T024-050661-2026-11-09-mask-sensitivity.json).

Reproduce the overlay from the repository root:

```bash
.venv/bin/python tools/research/evaluate_rtc_dswx_spatial_support.py \
  --pair data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json \
  --optical data/research/dswx-hls-rtc-aoi-context-2026-11-07.json \
  --output /tmp/t024-spatial-support.json
```

The active case manifest selects the assessment that includes this overlay. Tests recompute the retained T024 overlay and validate the assessment's linked evidence. Neither result changes the pair's diagnostic QA status or resolves the physical explanation.
