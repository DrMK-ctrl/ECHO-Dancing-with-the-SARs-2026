# NISAR VALIDATED GCOV temporal pair: QA disposition

## Catalog result

The paginated global ASF scan identified one metadata-compatible pair in the current VALIDATED GCOV release:

| Role | Acquisition start (UTC) | Orbit | Product |
|---|---|---:|---|
| Before | 2026-10-24 22:49:55 | 6511 | `NISAR_L2_PR_GCOV_034_011_A_017_4005_DHDH_A_20261024T224955_20261024T225027_P05036_N_F_J_001` |
| After | 2026-11-05 22:49:56 | 6684 | `NISAR_L2_PR_GCOV_035_011_A_017_4005_DHDH_A_20261105T224956_20261105T225027_P05036_N_F_J_001` |

Both are in `NISAR_L2_GCOV_V1` / CRID `P05036`, ascending path 11, frame 17, full-frame coverage, and catalog HH/HV polarization. Their catalog footprints intersect and their acquisition starts are 12 days apart. This establishes metadata compatibility only.

### Pair-gap sensitivity check

Using the retained 993-scene paginated catalog snapshot, ECHO's unchanged metadata compatibility rules returned the same single pair with `max_gap_days=24` and `max_gap_days=365`. Thus widening the interval threshold did not expose a second pair in this snapshot; the 24-day setting is not the cause of the current pair scarcity. This is bounded to the October 21–November 7 VALIDATED catalog scan and does not establish global temporal coverage beyond it. The input catalog and pairing-code checksums, both run counts, and exact candidate are recorded in [`validated-gcov-pair-gap-sensitivity-2026-11-07.json`](../../data/research/validated-gcov-pair-gap-sensitivity-2026-11-07.json).

## Product QA and hold

ASF's canonical QA summary for each product reports the identification-group check as **FAIL**. The remaining eight summary checks pass. The 1,441-byte summary artifacts have SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688` for both products. The full, product-specific QA reports were retrieved and parsed:

- Before report: SHA-256 `2bbc5b21477c68b2bee038c455f3e188615dc62f637f80d98209495e3bafb9bb`; QA software 17.2.0.
- After report: SHA-256 `e166ac1820bafba6c9f2fe045396ec4763a9a0794aee5825cf984d83bb934c1d`; QA software 17.2.0.

Both reports record `instrumentName=LSAR` and `listOfObservationModes=["(NOT SPECIFIED)"]`. A partial cross-check against the published `nisarqa` v17.2.0 validation rules finds that each value conflicts with a corresponding validator rule. This is diagnostic source-code evidence, not provider per-field QA evidence; it does not supersede ASF's aggregate FAIL.

Upstream implementation history makes a writer/validator schema mismatch a plausible explanation for at least these failures. The products report ISCE3 processing software 0.25.21; that release's notes say the default instrument name for STATIC products changed from `L-SAR` to `LSAR`, while `nisarqa` v17.2.0 still accepts only `L-SAR` or `S-SAR`. A live source check on 2026-11-07 found the same mismatch in the current public branches: ISCE3 `develop` still documents `LSAR` as the STATIC default, and `nisarqa` `main` still allows only `L-SAR` or `S-SAR`. Separately, an earlier ISCE3 GCOV QA issue records both an `LSAR` allowlist error and `(NOT SPECIFIED)` observation-mode errors from QA output. These sources corroborate the same incompatibilities but do not expose the per-field results for this pair or establish that these are the only failing identification checks. ECHO therefore retains the provider `FAIL` and continues to block comparison.

Supporting upstream sources: [ISCE3 v0.25.21 release notes](https://github.com/isce-framework/isce3/releases/tag/R05.03.2), [ISCE3 STATIC defaults at `8a6bf71`](https://github.com/isce-framework/isce3/blob/8a6bf71b03f4327143fa2c890a2f38d3774acc52/share/nisar/defaults/static.yaml), [ISCE3 GCOV issue #216](https://github.com/isce-framework/isce3/issues/216), [`nisarqa` v17.2.0 identification checks](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py), and [`nisarqa` identification checks at `a8bc425`](https://github.com/isce-framework/nisarqa/blob/a8bc425f5e8873174471d6a12fe622df338623d1/src/nisarqa/validate/sanity_checks.py).

ECHO held both roles at the provider QA gate. It read neither product metadata arrays nor radar measurement arrays for this pair. There is no temporal measurement, and no change result is asserted. The precise QA summaries, report metadata, product identifiers, retrieval records, and interpretation boundary are preserved in [`validated-gcov-temporal-pair-qa-review-2026-11-07.json`](../../data/research/validated-gcov-temporal-pair-qa-review-2026-11-07.json).

## Next evidence needed

The pair now removes global catalog truncation as the immediate explanation for the absence of a comparison. The remaining NISAR gate is the provider identification QA failure. A provider correction or explicit authoritative disposition is needed before ECHO can run a pair measurement. Any later release or corrected product must be searched and QA-screened as a distinct source record; these failed product records remain preserved.
