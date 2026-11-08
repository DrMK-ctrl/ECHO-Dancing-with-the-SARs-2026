# Decision 0029: compare RTC-S1 polarizations on shared evidence support

**Status:** Implemented as a diagnostic research evaluation; not a QA or scientific acceptance decision.

## Context

The retained T163-349925-IW2 Sentinel-1 pair has both VV and VH Gamma0 COGs for each acquisition. A same-pair polarization comparison can test whether a weak SAR-to-optical spatial association is sensitive to the measured polarization without searching for a new scene pair. It cannot provide independent validation because both channels share the acquisitions, RTC-S1 processor, geometry, and much of the error structure.

## Decision

Retrieve a bounded VH window with the existing authenticated reader, use the same AOI and product-mask rules as VV, and compare the area-weighted DSWx-HLS associations only on cells valid in both polarizations and meeting the same optical coverage threshold. Preserve both as diagnostic. Do not combine the channels into a new classifier or interpret their agreement as independent confirmation.

## Observed result

Both polarizations have 1,199 valid AOI measurements. On the same 738 cells with at least 75% common-valid optical area, the descriptive Pearson correlations between optical water-fraction change and SAR log-ratio are −0.108 for VV and −0.078 for VH. The per-cell VV/VH log-ratios correlate at 0.644. VH minus VV has median 0.161 dB and median absolute deviation 1.655 dB. The water-fraction change median is zero. These are descriptive diagnostics; no inferential statistic is computed because cells are spatially dependent.

The result does not establish or exclude a water-related cause. The optical WTR classes are algorithm context, not field truth or SAR validation. The RTC-S1 source sidecars still provide no consolidated provider PASS/FAIL disposition. The investigation remains unresolved.

## Consequences

- The T163 case assessment now links the VH pair, VH spatial overlay, and sensitivity artifact to the water hypothesis as `DOES_NOT_DISTINGUISH`; its overall disposition remains unresolved.
- The interface shows the common-support metrics and provides separate source inspectors for the sensitivity analysis, VH measurement pair, and VH spatial overlay.
- If polarization materially changes a finding in a future case, investigate acquisition geometry, scattering mechanism, calibration, and product QA before assigning physical meaning.

## Reproduction

```bash
.venv/bin/python tools/research/evaluate_rtc_dswx_spatial_support.py \
  --pair data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --output data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-2026-11-08.json
.venv/bin/python tools/research/evaluate_rtc_dswx_spatial_support.py \
  --pair data/research/opera-rtc-live-pair-T163-349925-IW2-VH-2024-11-08.json \
  --optical data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --output data/research/opera-rtc-dswx-spatial-support-T163-349925-VH-2026-11-08.json
.venv/bin/python tools/research/evaluate_rtc_polarization_sensitivity.py \
  --vv data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-2026-11-08.json \
  --vh data/research/opera-rtc-dswx-spatial-support-T163-349925-VH-2026-11-08.json \
  --output data/research/opera-rtc-polarization-sensitivity-T163-349925-2026-11-08.json
```
