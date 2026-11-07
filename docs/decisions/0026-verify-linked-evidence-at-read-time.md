# Decision 0026: Verify linked evidence when loading an assessment

**Date:** 2026-11-08
**Status:** Implemented for local cross-sensor assessments

## Context

Assessment records store relative paths, SHA-256 checksums, source record types, roles, and dispositions for their evidence artifacts. Before this change, the local interface validated hypothesis relationships but did not confirm that the linked files still existed or matched the recorded identities. A source record could change after assessment generation while the old interpretation continued to appear current.

## Decision

- Before serving an assessment, resolve every evidence path beneath the configured project root and reject absolute or escaping paths.
- Enforce a per-artifact read limit, verify the SHA-256 checksum, parse the source JSON, and confirm its record type and disposition against the assessment manifest.
- Reject missing, changed, oversized, or identity-mismatched evidence with an explicit service error; rebuild the assessment against the corrected source record before presenting it again.
- Preserve each evidence artifact's declared role. This verifies record integrity and provenance links, not provider truth or scientific validity.

## Verification

- Synthetic endpoint cases verify valid linked evidence is served, stale hypothesis dispositions are rejected, and a changed source checksum fails closed.
- Both retained Rio Grande do Sul case assessments load through the local endpoint with their source artifacts verified: T024 has four artifacts and T163 has three.
- The implementation caps each linked JSON artifact at 64 MiB to keep request-time verification bounded.
