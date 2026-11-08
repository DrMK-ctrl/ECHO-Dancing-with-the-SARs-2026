# Link GCOV catalog screens to open follow-up tests

**Status:** Accepted

## Context

Investigation drafts can define a single-hypothesis follow-up test, and ASF search already discovers NISAR GCOV catalog metadata. Until now, those capabilities were separate: users had to leave the draft, search independently, and manually import a record. That gap made it difficult to preserve which test motivated a search.

## Decision

An unassessed draft with an open discriminating follow-up can launch the existing ASF GCOV catalog search. The catalog dialog identifies the linked follow-up and target hypothesis, and the user chooses the date interval and maturity. The search record is attached to the draft with the follow-up ID, target hypothesis, and canonical test-design checksum.

The attached record is explicitly `CATALOG_AVAILABILITY_METADATA_ONLY`. It records the query, response, feature count, truncation state, timestamp, and checksums. Test fit and source independence are machine-marked `NOT_ASSESSED_METADATA_ONLY`; the query is an optional availability check, not a recommendation that GCOV is appropriate for the test. It does not represent retrieved radar pixels, provider QA, compatibility, or source suitability. Draft validation rejects directional hypothesis relationships and follow-up gate screening against this role. A search with no matches moves the follow-up to `SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE`; a search with one or more candidate scenes moves it to `CANDIDATE_RETRIEVED_UNASSESSED`. Both states retain the catalog evidence reference and leave hypotheses and gate results unassessed. The user must save the updated private snapshot to persist it across sessions.

## Consequences

- The search result remains inspectable as a linked source in the investigation draft.
- The map and timeline continue to show the catalog response after the search.
- A catalog match cannot be presented as scientific support or as a successful test.
- Results may be incomplete when the ASF result cap is reached; that state is retained.
- This is an availability-discovery step. Product retrieval, QA review, compatibility checks, and scientific screening remain separate work.

See [validation record](../validation/followup-gcov-catalog-screen-2026-11-08.md).
