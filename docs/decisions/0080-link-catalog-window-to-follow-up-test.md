# Decision 0080: link a planned catalog window to the follow-up test

**Date:** 2026-11-08
**Status:** Accepted

## Context

An investigation draft pre-registers one hypothesis, expected and weakening observations, and data acceptance gates. The optional ASF catalog search is linked to that test, but its date interval was selected separately in the search dialog. The retained catalog query records the dates actually used, while the test itself had no structured date target.

## Decision

Add an optional inclusive start/end date window to the follow-up test design. Validate canonical `YYYY-MM-DD` dates and their order, then include the window in the checksummed test design. When the linked ASF GCOV search opens, prefill its date controls from this window. Keep the controls editable and retain the exact executed query against the test-design checksum. Linked drafts without a planned window remain valid and keep their existing search defaults. A revised draft carries its parent's window forward.

## Consequences and limits

- The proposed interval becomes visible beside the hypothesis test and in the linked catalog-search context.
- The planned dates are a discovery filter, not evidence of an expected acquisition, coverage, product suitability, or temporal compatibility.
- Catalog results remain metadata-only and cannot satisfy acceptance gates or alter a hypothesis state.
- The geographic search area continues to come from the selected SAR investigation area; this decision does not add a new geometry model.

See [validation](../validation/follow-up-catalog-window-2026-11-08.md).
