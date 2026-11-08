# Preview counterfactual evidence reclassification

**Date:** 2026-11-08
**Status:** Implemented; local API, deterministic tests, and Firefox interaction verified

## Context

The investigation view records structured analyst challenges, but those notes do not show whether a challenged evidence interpretation could affect the current hypothesis disposition. Automatically changing a retained assessment would overstate what an unverified user assertion establishes.

## Decision

Add an explicitly counterfactual preview for one evidence artifact already cited by the selected hypothesis. The analyst may propose a different evidence relationship; ECHO applies the same deterministic relationship rule used by the stored assessment and shows the resulting disposition. The preview is bound to the active assessment's case ID and SHA-256. Evidence choices are limited to the selected hypothesis's existing references.

The preview is read-only. It does not change the retained assessment, source artifact, provider QA, or evidence relationships. If the analyst saves a challenge note, the preview result is shown beside that note and included in the unassessed human-input JSON export, linked to the assessment and source checksums.

## Interpretation boundary

The scenario answers: “What disposition would the current rule produce if this existing evidence item had a different analyst-coded relationship?” It does not answer whether that relationship is scientifically correct, add missing evidence, change source quality, establish causality, or create an updated scientific finding. The user must review the source and rationale independently.

The view labels the result `COUNTERFACTUAL_ONLY`, states that no source or finding changed, and retains the original assessment unchanged. It provides a narrow analyst-controlled challenge loop; it is not an autonomous Investigation Engine.

## Verification

- Unit cases show a single relationship change can alter a one-item fixture's disposition, while unrelated limiting evidence keeps a hypothesis unresolved.
- The API validates the current assessment and source artifacts, rejects an assessment checksum mismatch, and returns a read-only counterfactual record.
- Firefox opened the T163 investigation, selected a cited evidence record, changed its proposed relationship, and displayed the counterfactual disposition and limitation text.
- The saved session note displays the same counterfactual result, and the export retains the preview record with the source and assessment hashes.
- The HTTP integration fixture confirms the assessment bytes remain unchanged after preview.
