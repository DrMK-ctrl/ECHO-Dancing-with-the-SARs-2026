# Select reviewed local investigation cases

**Date:** 2026-11-08  
**Status:** Implemented; full software verification pending

## Context

The investigation reasoning view and evidence contracts had been exercised against T024 and T163, but the application still loaded a single case selected at server startup. That made cross-case workflow inspection require restarting ECHO and made the UI feel more like a prepared demonstration than a reusable investigation workspace.

## Decision

Expose reviewed case records through a local registry and let the user select a case by its stable case ID. Resolve IDs to catalog paths on the server; do not accept paths from browser requests. Carry the selected ID through case-dependent API requests so catalogs, reviews, QA reports, and linked investigation evidence stay scoped to the selected case. Preserve each case's existing QA and interpretation status.

When the selected case declares a linked assessment, expose a case-level action to open that investigation directly. The user should not need to enable an optical map layer to discover the assessment. Cases without an assessment do not show the action.

This step supports navigation and evidence inspection across retained cases. It does not make case data scientifically interchangeable, generalize product-specific measurement workflows, or establish an end-to-end investigative engine.

## Verification

- The local server's automatic registry discovery includes both T024 and T163 alongside other reviewed local cases.
- HTTP integration coverage verifies the registry's default case, T024/T163 assessment selection, and a 404 for an unknown case ID.
- Headless Firefox verified the selector changing from T163 to T024, the case-level action appearing for both assessment-linked cases, both assessment records opening through that action, and the action staying hidden for Nepal, which has no linked assessment. Detailed visual layout review remains open.
- Existing scientific assessments and QA records are read through their original case-local manifests; this change does not modify measurement or QA results.

See [multi-case selector validation](../validation/multi-case-selector-2026-11-08.md).
