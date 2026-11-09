# Decision 0094: link independent soil-moisture availability screens

**Date:** 2026-11-09
**Status:** Implemented

## Context

T024's H3 soil-moisture explanation had NASA SMAP L4 regional model context, but the follow-up did not retain exact case-scoped ECOSTRESS catalog queries or ISMN station-coverage evidence. The shared assessment builder also linked those routes only in the branch that had precipitation context, coupling evidence discovery to an unrelated source.

## Decision

Retain the bounded NASA CMR responses and the exact public ISMN inventory used for the T024 availability screen. Recompute target-query counts, pagination, response hashes, station distances, and inventory summaries during assessment construction and web validation. Link these records to the independent H3 follow-up as availability limits; they are not soil-moisture measurements and must not change H3's scientific disposition.

The screen linkage now works independently of whether GPM precipitation context is included. An absent or distant candidate keeps the search open; it does not imply that all sources are unavailable.

## Validation

See [T024 soil-moisture source availability](../validation/t024-independent-soil-moisture-availability-2026-11-09.md).
