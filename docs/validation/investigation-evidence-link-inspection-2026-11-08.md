# Investigation evidence-link inspection

**Date:** 2026-11-08
**Result:** Hypothesis citations and dependency records open through the linked evidence inspector

## Procedure

Started the local ECHO server against the T163 case and opened it in Firefox headless. Opened NASA optical context, then the matching cross-sensor assessment. The investigation rendered 16 `.investigation-source-link` controls. Clicking a hypothesis citation opened its linked NASA DSWx-HLS context record in the source inspector. Closing that inspector and clicking a record in the dependency panel opened the linked RTC-S1 pair-analysis record.

The source records were retrieved through the existing local evidence endpoint, which checks registered artifact identity and its SHA-256 before serving. The interface change did not modify case files or evidence relationships.

## Limits

This validates the UI path from an evidence relationship or dependency entry to its linked record. It does not validate the scientific truth of the relationship, provider QA, or the diagnostic RTC-S1 comparison. The T163 causal interpretation remains unresolved.
