# Decision 0061: Import validated case sources into investigation drafts

**Date:** 2026-11-08  
**Status:** Implemented for direct evidence linked to a validated local OPERA RTC-S1 case assessment

## Context

Investigation drafts could attach arbitrary local JSON records, but had no controlled path to use evidence already retained by an ECHO case. Re-entering those records loses their connection to the case assessment and creates avoidable copying and provenance errors. Import must not imply that the provider was contacted again or that a case contract check proves source suitability or independence.

## Decision

Allow the active case's direct evidence records to be offered for import only after ECHO revalidates the case assessment and linked record paths and checksums. Require the draft's OPERA RTC-S1 before/after scene IDs to match the case's assessed pair exactly. Exclude primary SAR records and records declaring derivation or shared-observation links. Preserve the case role, source status, assessment identity, source identity, paths, checksums, and import timestamp. Label the state `CASE_RECORD_INTEGRITY_VALIDATED`, retain independence as `NOT_ASSESSED`, and show that provider data was not reverified. The absence of recorded lineage links does not establish independence.

At draft assessment time, revalidate the active case assessment and source artifact against the import record. A changed case assessment, scene pair, source path, or source checksum invalidates the draft assessment request. Retain imported JSON as its exact source text so its file checksum remains stable across browser JSON number serialization; parse it only for display and structural checks.

## Consequences

- Existing case evidence can be linked to hypotheses without a second manual upload, while retaining source roles and status.
- Import integrity is bounded to local case records and their linked validation. It does not authenticate the provider, re-fetch the source, independently validate the scientific content, or establish independence.
- Only direct records from the active case and the exact matching OPERA RTC-S1 pair are eligible. Other SAR products and derived evidence remain outside this import path until their lineage and compatibility rules are explicit. Eligibility does not assert source independence.
- Draft assessments remain analyst-authored, provisional, and export-only.

## Verification

See [case-evidence import validation](../validation/investigation-case-evidence-import-2026-11-08.md).
