# Adversarial sensitivity summary reproduction

**Date:** 2026-11-12  
**Scope:** T163 diagnostic RTC-S1 investigation  
**Disposition:** Recomputed summaries match retained checksummed per-cell records; the case remains diagnostic and unresolved.

## Change

The Challenge This Finding builder previously verified the sensitivity files' checksums and source links, then displayed their stored summary fields. It now recomputes the values shown in the T163 challenge from the linked per-cell records:

- For VV optical-support sensitivity, ECHO reapplies each recorded common-valid WTR coverage threshold to valid per-cell SAR and water-fraction changes, then recomputes sample counts, change bins, means, medians, and descriptive Pearson correlation.
- For the VV/VH comparison, ECHO validates the shared cell grid and water-context support, applies the recorded 75% coverage threshold, selects cells valid in both polarizations, and recomputes the displayed medians, means, correlations, and VV-to-VH difference summaries.
- The challenge fails closed when a retained summary does not reproduce from its linked per-cell values.

The UI identifies these as **recomputed from checksum-validated per-cell records**. The source files, checksums, processing lineage, and interpretation limits remain inspectable.

## Retained case result

The VV coverage variants reproduce at 50%, 75%, 90%, and 95% minimum common-valid WTR area. Their selected SAR cell counts are **826, 738, 738, and 738**. At 75% and above, all four recorded bins reproduce: 14 increases greater than 0.05, 14 decreases less than −0.05, and 710 changes within ±0.05. The descriptive Pearson correlation at those thresholds reproduces as approximately **−0.108**.

On the 738-cell VV/VH common cohort, the recomputed VV and VH median log-ratios are **−1.215 dB** and **−1.144 dB**, respectively. Their descriptive Pearson correlation is approximately **0.644**. These are diagnostic summaries of related polarizations from the same Sentinel-1 acquisitions and processing chain; they are not independent corroboration.

## Verification

- Focused adversarial tests: **15 passed**.
- Full suite: **463 passed**.
- Browser-renderer test confirms the new reproduction basis is visible with the summary values.
- Tampering tests alter stored sensitivity statistics while retaining source per-cell values; ECHO rejects the mismatch.
- `git diff --check`: passed.

## Limits

This step reproduces statistics from the retained per-cell outputs. It does not recompute the original SAR log-ratio rasters, rerun the native-grid DSWx-HLS polygon overlay, revalidate source pixels, or determine whether the analyst's evidence relationships are scientifically correct. OPERA has no consolidated provider PASS/FAIL disposition in this case; its result remains diagnostic. Optical classes remain context, not field truth or SAR validation. No causal or flood finding is produced, no confidence score is calculated, and the QA-held Iraq NISAR case is unchanged.
