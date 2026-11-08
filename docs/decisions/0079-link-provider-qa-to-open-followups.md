# Link provider QA records to open follow-up tests

**Status:** Accepted

## Context

An investigation draft could retain an ASF NISAR GCOV availability search linked to a pre-registered follow-up, but the user had to leave that draft to inspect provider QA for a returned scene. That broke the visible evidence chain between the searched candidate, the provider's own quality disposition, and the test that motivated the search.

## Decision

For an unassessed draft with an open discriminating follow-up, the user may select a scene from a retained NISAR GCOV catalog result and stage its ASF provider QA into that same draft. The local ECHO backend resolves the selected ID against the retained catalog response, validates its ASF product URL, retrieves the canonical bounded QA CSV through the existing Earthdata-authenticated reader, and retains the parsed response and byte checksum. The staged record must match the exact catalog feature and scene ID, retain the parent catalog record checksum, link to the same follow-up and test-design checksum, and retain a checksum of the inspection record.

The source role is `FOLLOWUP_PROVIDER_QA_METADATA_ONLY`. Its wrapper records `ASF_QA_CSV_RETRIEVED_BY_ECHO_AT_ATTACHMENT`; this identifies a successful bounded retrieval from the allowlisted ASF HTTPS product path and retained bytes, not a validation of the provider's QA interpretation or ECHO's product suitability decision. The source inspector exposes the provider disposition and retrieval record. Provider QA metadata cannot directionally support or contradict hypotheses and cannot satisfy follow-up acceptance gates. Staging leaves the follow-up and hypothesis assessment states unchanged; the user must save the updated private snapshot to persist it.

## Consequences

- A candidate's catalog metadata and provider QA inspection remain traceably linked to the specific follow-up that prompted discovery.
- Provider disposition, including `FAIL`, remains intact and distinguishable from ECHO's scientific compatibility assessment.
- No product raster or radar measurement is retrieved by this linkage step, and QA is not treated as evidence for a physical mechanism.
- The attachment checksum detects later changes to the retained QA record. The retrieval record captures the network path and checksum; the provider disposition still does not establish test compatibility or event interpretation.

See [validation record](../validation/followup-provider-qa-link-2026-11-08.md).
