# Decision 0064: Save private local investigation snapshots

**Date:** 2026-11-08
**Status:** Implemented for validated immutable local snapshots; cross-device synchronization and deletion controls remain out of scope

## Context

Investigation drafts could be exported and restored manually, but ECHO did not retain them between sessions. That made repeated source inspection and evidence review depend on managing large JSON files by hand. A local snapshot should preserve the full draft and its embedded source records while maintaining the same validation boundaries as import and restore.

## Decision

Add explicit save, list, and reopen actions for investigation drafts in the local application. Store canonical JSON snapshots under the user's XDG data directory, outside the source repository. Identify each immutable snapshot by the SHA-256 of its stored bytes; a changed draft creates a new snapshot while an identical draft deduplicates. Restrict storage API calls to loopback clients and set the directory and file permissions to `0700` and `0600` on POSIX systems. Apply per-draft, record-count, and total-size limits.

Saving and reopening validate the draft contract. Any imported case sources must still match the selected case's retained assessments and source artifacts when saved or reopened. Checksums establish byte integrity only; they do not authenticate an analyst, provider, source independence, scientific suitability, or an evidence relationship.

## Consequences

- A local investigation can be resumed across application sessions without manual file handling.
- Snapshots are immutable and content-addressed, preserving a review trail without silently overwriting earlier drafts.
- Export/import JSON remains available for portability and backup.
- Local snapshots are not synchronized, backed up, or deleted by ECHO. The user can manage the local data directory outside the application.
- Storage is available only through the loopback interface. Binding the application to a network address does not expose these draft endpoints to remote clients.

## Verification

See [private local draft persistence validation](../validation/local-investigation-draft-persistence-2026-11-08.md).
