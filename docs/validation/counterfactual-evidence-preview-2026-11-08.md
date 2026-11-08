# Counterfactual evidence-reclassification preview

**Date:** 2026-11-08
**Disposition:** Local interactive preview verified; scientific re-evaluation is not performed

## Procedure and result

The preview helper was tested with two declared synthetic fixtures. Reclassifying the only cited item changed `SUPPORTED_WITHIN_SCOPE` to `CONTRADICTED_WITHIN_SCOPE`; reclassifying one of two items left the disposition `UNRESOLVED` when the other item still limited interpretation. An uncited source is rejected. The helper left its input hypothesis unchanged.

The local API was exercised against a checksummed synthetic assessment. It returned record type `ECHO_COUNTERFACTUAL_EVIDENCE_RECLASSIFICATION_PREVIEW` and state `COUNTERFACTUAL_ONLY`. The test confirmed the assessment file bytes were unchanged and a stale assessment checksum received HTTP 409.

Firefox opened the retained T163 assessment, selected a source already cited by the chosen hypothesis, changed its proposed relationship, and displayed:

`SUPPORTED WITHIN SCOPE → CONTRADICTED WITHIN SCOPE`

The rendered preview identified the selected NASA OPERA DSWx-HLS context item and stated that no source or finding changed. This is the output of an analyst-entered counterfactual, not a revised scientific conclusion.

The reviewer then saved a challenge note. The assessment view displayed the same counterfactual transition under the note's `UNASSESSED HUMAN REVIEW` label. Exporting the notes retained the counterfactual response, the cited evidence identifier and checksum, and the original assessment checksum in a downloadable JSON record.

## Scope limits

The preview changes exactly one analyst-coded relationship in memory. It does not alter observation data, source QA, evidence status, or the saved assessment. It does not verify the proposed relationship, assign probabilities, infer causality, or add a missing source. Any saved challenge note remains `UNASSESSED_HUMAN_INPUT` and must be exported to persist beyond the browser session.
