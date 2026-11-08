# Decision 0062: Restore exported investigation drafts

**Date:** 2026-11-08  
**Status:** Implemented for downloaded JSON drafts; server-side persistence remains open

## Context

Investigation drafts could be downloaded with their source records and analyst-entered review, but the interface could not reopen them. That made a multi-session investigation dependent on one browser session and weakened reproducibility. Restore must verify the stored contract and checksums, and it must not treat an old local case link as current without checking it again.

## Decision

Add an explicit **Open saved draft JSON** action. The server validates the draft contract and each embedded source checksum before returning a draft to the interface. For a case-imported source, restore also requires the currently selected case to match the recorded active case, revalidates its assessment and exact OPERA RTC-S1 scene pair, and rechecks each source artifact path, identity, and checksum. A missing or changed case source prevents restore; the application does not silently accept the embedded copy as current case evidence.

Retain the exact primary SAR JSON text supplied at draft creation and checksum those bytes. The UI also embeds this exact text in its exported draft. This avoids checksum drift when JavaScript serializes numeric JSON values such as `1.0` as `1`. Direct Python callers that do not supply the original text continue to use canonical JSON serialization.

## Consequences

- Unassessed or analyst-assessed drafts can be resumed from a downloaded JSON file after integrity checks.
- Restoring an assessed draft preserves its analyst-authored relationships but continues to label them unverified.
- Case-imported sources are accepted only while their recorded case link and local source artifact still validate against the selected case.
- Drafts remain user-managed files; ECHO does not keep server-side draft history or silently autosave to disk.
- Checksums establish byte consistency, not authorship, provider authenticity, source independence, or scientific validity.

## Verification

See [investigation-draft restore validation](../validation/investigation-draft-restore-2026-11-08.md).
