# Decision 0081: record executed catalog-window alignment

**Date:** 2026-11-08  
**Status:** Accepted

## Context

Decision 0080 links an optional planned date interval to one hypothesis-specific follow-up test and pre-fills the ASF catalog search. The search controls remain editable, so the retained query can use different dates. Without recording the relationship, the investigation could display a plan and a search without making their divergence obvious.

## Decision

When attaching a follow-up catalog screen, record its planned inclusive interval, the executed query interval, and a deterministic state: no planned interval, matching interval, or deviation. Validate that record against both the retained catalog query and the current checksummed follow-up design. New catalog-screen records use schema version 2 and require this comparison; existing version 1 records remain readable without it.

Render the comparison beside the linked follow-up evidence, labeling it as a date-filter comparison only. Keep the original query and catalog response as the source record.

## Consequences and limits

- An edited query remains usable, but its divergence from the registered test interval is explicit and tamper-checked.
- The comparison establishes only whether the submitted start/end filters match the planned dates. It does not establish catalog coverage, scene acquisition dates, suitability, compatibility, or product QA.
- Catalog records remain metadata-only and cannot satisfy scientific acceptance gates or alter hypothesis assessments.
- Existing version 1 investigation snapshots remain valid for backward compatibility.

See [validation](../validation/follow-up-catalog-window-alignment-2026-11-08.md).
