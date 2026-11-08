# Link provider QA records to open follow-up tests

**Status:** Accepted

## Context

An investigation draft could retain an ASF NISAR GCOV availability search linked to a pre-registered follow-up, but the user had to leave that draft to inspect provider QA for a returned scene. That broke the visible evidence chain between the searched candidate, the provider's own quality disposition, and the test that motivated the search.

## Decision

For an unassessed draft with an open discriminating follow-up, the user may select a scene from a retained NISAR GCOV catalog result and stage its existing ASF provider-QA inspection into that same draft. The staged record must match the exact catalog feature and scene ID, retain the parent catalog record checksum, link to the same follow-up and test-design checksum, and retain a checksum of the inspection record.

The source role is `FOLLOWUP_PROVIDER_QA_METADATA_ONLY`. Its wrapper records `RETRIEVAL_PROVENANCE_RETAINED_NOT_REVERIFIED_AT_ATTACHMENT`: the draft API links the supplied inspection snapshot but does not re-contact ASF or independently verify that earlier retrieval. The source inspector exposes the provider disposition and retrieval record with that limitation. Provider QA metadata cannot directionally support or contradict hypotheses and cannot satisfy follow-up acceptance gates. Staging leaves the follow-up and hypothesis assessment states unchanged; the user must save the updated private snapshot to persist it.

## Consequences

- A candidate's catalog metadata and provider QA inspection remain traceably linked to the specific follow-up that prompted discovery.
- Provider disposition, including `FAIL`, remains intact and distinguishable from ECHO's scientific compatibility assessment.
- No product raster or radar measurement is retrieved by this linkage step, and QA is not treated as evidence for a physical mechanism.
- The attachment checksum detects later changes to the retained QA record but does not authenticate the provider response or revalidate its retrieval.

See [validation record](../validation/followup-provider-qa-link-2026-11-08.md).
