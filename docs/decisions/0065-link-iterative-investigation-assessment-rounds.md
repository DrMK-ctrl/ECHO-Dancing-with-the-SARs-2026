# Decision 0065: Link iterative investigation assessment rounds

**Date:** 2026-11-08  
**Status:** Implemented for saved local investigation drafts

## Context

An investigation draft could record one provisional assessment and preserve it as an immutable local snapshot, but the interface had no direct path from that assessment to a subsequent evidence review. Starting over could lose the relationship between the earlier assessment and the next test. A revision must preserve the earlier record and require fresh, explicit assessment of carried evidence.

## Decision

Allow a user to start a new round from a saved, analyst-assessed draft. The new round retains the exact source records, source checksums, case-import provenance, question, and hypothesis definitions. It clears active hypothesis dispositions and evidence relationships, requires a newly specified follow-up test aimed at one hypothesis, and records the parent snapshot checksum, parent assessment checksum, revision number, and UTC creation time.

The prior snapshot is immutable. Saving, reopening, and restoring a revision verifies that its parent snapshot exists, its checksum is valid, the parent is analyst-assessed, its assessment checksum matches, and the revision number follows the parent. Case-imported sources are revalidated against the active case. The new round remains an unauthenticated analyst draft; no measurement, relationship, QA disposition, or finding is promoted.

## Consequences

- Evidence can be added to a new round and reconsidered against the same competing hypotheses without erasing the prior assessment.
- A revision starts with every hypothesis `NOT_EVALUATED`; previous analyst relationships remain only in the immutable parent.
- A revision currently requires its parent snapshot to be present in the same local store. For exported revisions, restore the parent first. This is local snapshot lineage, not synchronized case history.
- The workflow records analyst reasoning; it does not determine whether a relationship or physical explanation is true, and it does not retrieve the planned observation automatically.
- Each round still registers one discriminating follow-up test against exactly one hypothesis.

## Verification

See [the draft revision validation](../validation/investigation-draft-revisions-2026-11-08.md).
