# Adversarial sensitivity summary reproduction

**Date:** 2026-11-12  
**Scope:** T163 diagnostic RTC-S1 investigation  
**Disposition:** Recomputed summaries match retained checksummed per-cell records; the case remains diagnostic and unresolved.

## Change

The Challenge This Finding builder previously verified the sensitivity files' checksums and source links, then displayed their stored summary fields. It now recomputes the values shown in the T163 challenge from the linked per-cell records:

- For VV optical-support sensitivity, ECHO reapplies each recorded common-valid WTR coverage threshold to valid per-cell SAR and water-fraction changes, then recomputes sample counts, change bins, means, medians, and descriptive Pearson correlation.
- The challenge also calculates a fixed exploratory sweep from 50% through 95% in five-percentage-point steps from the same per-cell measurements. The four source-recorded thresholds are still independently reproduced and checked; the added sweep does not select a preferred cutoff.
- For the VV/VH comparison, ECHO validates the shared cell grid and water-context support, applies the recorded 75% coverage threshold, selects cells valid in both polarizations, and recomputes the displayed medians, means, correlations, and VV-to-VH difference summaries.
- The challenge fails closed when a retained summary does not reproduce from its linked per-cell values.

The UI identifies the sweep as calculated from checksum-validated per-cell measurements. It labels the values descriptive and states that they do not establish flood extent, causation, or provider QA clearance. The source files, checksums, processing lineage, and interpretation limits remain inspectable.

## Retained case result

The VV coverage variants reproduce at 50%, 75%, 90%, and 95% minimum common-valid WTR area. Their selected SAR cell counts are **826, 738, 738, and 738**. At 75% and above, all four recorded bins reproduce: 14 increases greater than 0.05, 14 decreases less than −0.05, and 710 changes within ±0.05. The descriptive Pearson correlation at those thresholds reproduces as approximately **−0.108**.

On the 738-cell VV/VH common cohort, the recomputed VV and VH median log-ratios are **−1.215 dB** and **−1.144 dB**, respectively. Their descriptive Pearson correlation is approximately **0.644**. These are diagnostic summaries of related polarizations from the same Sentinel-1 acquisitions and processing chain; they are not independent corroboration.

## Verification

- At initial implementation, focused adversarial tests: **15 passed**; full suite: **463 passed**.
- Browser-renderer test confirms the original reproduction basis was visible with the summary values.
- Tampering tests alter stored sensitivity statistics while retaining source per-cell values; ECHO rejects the mismatch.
- `git diff --check`: passed.

## Exploratory support sweep — 2026-11-12

The challenge response now returns ten descriptive thresholds from 50% to 95% at five-percentage-point intervals. Counts and summary statistics are calculated on demand from the linked `per_sar_cell` record. At source-recorded thresholds, the calculated sweep agrees with the independently reproduced retained results: 826 cells at 50%, then 738 at 75%, 90%, and 95%. Undefined metrics render as unavailable. The UI does not label any threshold as optimal or turn these summaries into a stability score.

The focused adversarial suite now passes **19 tests**, including sweep range, monotonic retained-cell counts, agreement at all source-recorded cutoffs, rejection of missing SAR values marked valid, QA-held Iraq behavior, and existing checksum/tampering checks. Focused renderer plus adversarial tests pass **24 tests**; the full suite passes **470 tests** with `.venv/bin/python -m pytest -q`.

## Local browser walkthrough — 2026-11-12

A headless Firefox session opened the curated read-only T163 case, opened the case assessment, selected **Challenge This Finding** for the water-change explanation, and expanded **Comparability and Sensitivity**. The live challenge panel displayed ten rows from 50% to 95%, including 826 cells and −2.261/−1.316 dB mean/median at 50%, and 738 cells and −2.047/−1.215 dB at 95%. The “no cutoff is preferred” explanation, diagnostic disposition, and unresolved provider-QA state were present.

The spatial view draws from the same evidence. Its 1,254 cell records use the linked pair's 39×34 WGS84 corner grid. Before display, all 1,199 cells marked SAR-valid in the support record matched both pair validity masks, and their signed log-ratio values matched the checksummed pair measurement array exactly. The interactive 50% filter displays 826 cells; moving to 75% displays 738. Changing the layer switches between signed SAR log-ratio and DSWx-HLS optical water-fraction change; the legend identifies their separate scales. This is a spatially registered diagnostic comparison, not causal evidence. External basemap images were disabled during this check.

The interactive walkthrough moved the support control through every five-percentage-point step and compared visible cell counts against all ten table rows. Counts matched at every step: 826 cells from 50% through 65%, then 738 from 70% through 95%. The API returned the complete challenge dossier, including map geometry and per-cell values, in 317,699 bytes in approximately 0.14 seconds in this local run. The geometry is sent once as a shared corner grid rather than duplicated for each polygon. See the [captured view](assets/adversarial-spatial-sensitivity-2026-11-12.png).

## Limits

This step reproduces statistics from retained per-cell outputs and checks their SAR values against the checksummed pair measurement array. It does not recompute the original SAR log-ratio rasters, rerun the native-grid DSWx-HLS polygon overlay, revalidate provider source pixels, or determine whether the analyst's evidence relationships are scientifically correct. OPERA has no consolidated provider PASS/FAIL disposition in this case; its result remains diagnostic. Optical classes remain context, not field truth or SAR validation. No causal or flood finding is produced, no confidence score is calculated, and the QA-held Iraq NISAR case is unchanged.
