# Revalidate imported investigation review notes

**Date:** 2026-11-08
**Status:** Implemented; Firefox export/reload/import and tamper rejection verified

## Context

Challenge notes and their counterfactual previews could be exported, but they were limited to the browser page session. Reviewers could not restore a prior review after reload, and retaining an export alone did not show whether its assessment and source references still matched the open case.

## Decision

Allow JSON review-note exports to be imported into the active assessment session under strict bounds (1 MiB and 100 notes). Import requires the same case, exact assessment SHA-256, matching evidence IDs, roles, and source checksums, and a matching hypothesis definition and disposition. Notes remain unassessed human input.

For each included counterfactual preview, ECHO calls the existing read-only preview API again and compares the recorded source relationship and derived dispositions with the fresh result. Stale or altered previews reject the import before any notes are added. Duplicate notes are ignored. Imported notes remain in browser memory until re-exported; the case assessment and source records are never written.

## Verification

- Firefox exported a challenge note, reloaded the application, imported the export, and rendered the revalidated counterfactual under its unassessed label.
- The imported JSON retained matching assessment and evidence SHA-256 values.
- A copied export with a modified counterfactual disposition was rejected; no note was rendered.
- The browser remains read-only with respect to scientific case records.
