# Private local investigation draft persistence — 2026-11-08

## Result

Validated analyst-authored investigation drafts can be saved as immutable local snapshots, listed, and reopened through the local interface. The save and load path revalidates the draft contract and current case links. Snapshots remain explicitly unverified and outside the source repository.

## Evidence

- `LocalDraftStore` round-trip, content-address deduplication, tampered-byte detection, invalid-ID rejection, invalid-record rejection, and POSIX directory/file permissions: **3 focused tests passed**.
- Local HTTP API integration for save, list, reopen, and rejection of a modified invalid draft: passed.
- Full software test suite: **321 passed**.
- `.venv/bin/python -m compileall -q echo tests`: passed.
- Headless Firefox through a temporary local server: created a controlled `QA_HELD` draft, saved a snapshot, populated the private local draft list, reopened the saved record, and rendered `DRAFT_NOT_ASSESSED`. The server-side store contained one record.
- `git diff --check`: passed.

The browser fixture contains no Earth observation and does not assess a scientific interpretation. The app binds to loopback by default; local snapshot APIs independently reject non-loopback clients. On POSIX, the storage directory is mode `0700` and snapshot files are mode `0600`. The configured temporary store in the browser validation was isolated and removed when the run ended.

## Limits

- Local snapshots are not synchronized or backed up, and ECHO currently has no in-app deletion or retention interface.
- A snapshot checksum establishes integrity of the saved bytes, not authorship, source authenticity, independence, suitability, or correctness of analyst-entered relationships.
- Imported case sources are checked against the active case when saved and reopened. A changed or unavailable case source blocks restoration as current case-linked evidence.
- This validates draft persistence, not the completeness of the Investigation Engine or any scientific finding.
