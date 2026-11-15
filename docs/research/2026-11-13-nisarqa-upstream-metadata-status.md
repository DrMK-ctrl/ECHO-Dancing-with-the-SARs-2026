# NISAR GCOV identification-QA context: upstream status checked 2026-11-13

## Why this note exists

ECHO has retained repeated ASF product QA summaries whose aggregate identification-group result is `FAIL`, including NISAR GCOV products whose allowlisted HDF5 identification fields include `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`. This note refreshes the public validator/release context. It does **not** change any ASF product QA result or authorize analysis.

## Findings from public primary sources

- The public `nisarqa` releases page showed **v17.2.0** as the newest numbered package release when checked on 2026-11-13. Its release notes include the Product Specification 1.6.0 XML. The current release page also lists a newer `R05.03.1` release label, but its associated `nisarqa` tag is v17.2.0; these are separate release identifiers and should not be conflated. [Release page](https://github.com/isce-framework/nisarqa/releases)
- The tagged v17.2.0 identification checks accept only `L-SAR` or `S-SAR` for `instrumentName`; for non-InSAR products they check `listOfObservationModes` using the observation-mode validator. This makes `LSAR` inconsistent with the tagged software's instrument-name allowlist. The retained local source cross-check identifies the placeholder observation-mode string as inconsistent as well. [Tagged validator source](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py)
- ISCE3 issue [#216, “GCOV dataset and attribute issues”](https://github.com/isce-framework/isce3/issues/216) remained **Open** when checked. It documents a QP GCOV QA example that reports `(NOT SPECIFIED)` in `/science/LSAR/identification/listOfObservationModes`, along with many other HDF5 dataset and attribute concerns. This is public context that the placeholder has been treated as invalid by the cited checks; it is not a product-specific diagnosis for ECHO's retained scenes.
- The associated [`nisarqa` PR #155](https://github.com/isce-framework/nisarqa/pull/155) remained **Open** and showed requested reviews outstanding. It concerns general checks for empty datasets, placeholder strings, and attribute/dataset type conventions. It is not evidence that the provider has cleared or reprocessed any ECHO candidate.

## Interpretation for ECHO

The observations above make an upstream metadata-validation issue a plausible shared explanation for the repeated identification-group failures. They do not identify ASF's exact failing subchecks for any individual ECHO product. ASF's retained QA summary reports only the aggregate group result; therefore ECHO must continue to preserve provider `FAIL`, hold paired analysis where required by its gate, and refrain from changing the provider verdict based on a source-code cross-check.

The practical path forward is to screen newly released or materially reprocessed products for their own provider QA artifacts and metadata. Re-running the same query or re-reading the same products without a new release, corrected artifact, or product change is unlikely to add evidence. This note does not assume that future products will pass.

## Scope and reproducibility

- Public pages were read on 2026-11-13; no issue comment, pull request, or external message was submitted.
- No ECHO code, credentials, private repository material, or local project records were sent to these services.
- Product-level ECHO evidence remains in the exact retained QA records, including [`2026-11-13-iraq-validated-gcov-pair-qa.json`](../../data/research/2026-11-13-iraq-validated-gcov-pair-qa.json) and [`2026-11-13-iraq-provisional-gcov-pair-qa.json`](../../data/research/2026-11-13-iraq-provisional-gcov-pair-qa.json). Those artifacts, not this public-context note, establish the specific scenes' provider QA dispositions.
