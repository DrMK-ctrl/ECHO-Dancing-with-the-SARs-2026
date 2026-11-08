# Decision 0059: Stage source records without treating them as evidence

**Date:** 2026-11-08
**Status:** Local JSON source staging, integrity checks, and unreviewed-state display implemented; source suitability review remains open

## Context

Pair-linked investigation drafts could describe competing hypotheses and a pre-registered next observation, but could not retain another source record for later review. Allowing an arbitrary attached source to enter hypothesis references immediately would let unverified material affect deterministic dispositions.

## Decision

Allow a draft to stage a user-supplied local JSON record as `USER_SUPPLIED_SOURCE_NOT_REVIEWED`. ECHO stores the parsed record, canonical JSON SHA-256, attachment timestamp, and ingest method. It labels source review `NOT_REVIEWED` and independence `NOT_ASSESSED`. The interface presents the source's own status as **user-declared and unverified**.

Staging does not create evidence relationships, change hypothesis dispositions, or update the next-observation availability. The draft's primary SAR pair remains separately typed and retains its original QA and maturity status. A source may be staged only once; a draft supports at most twelve staged records and each selected JSON file is capped at 16 MiB.

## Consequences

- An analyst can preserve candidate contextual or scientific records alongside a draft for later inspection.
- Unreviewed records remain outside all hypothesis relationships and cannot change an assessment.
- Checksums identify the canonical parsed JSON content; they do not authenticate the submitter, provider, original file bytes, scientific reliability, relevance, or independence.
- The staging endpoint is not a provider retrieval or validation service. Source-specific suitability adapters and an explicitly reviewed relationship workflow remain open.

## Verification

See [the staged-source workflow validation](../validation/investigation-source-staging-2026-11-08.md).
