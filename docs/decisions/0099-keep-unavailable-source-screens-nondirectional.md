# Keep unavailable-source screens non-directional

## Decision

The shared investigation contract rejects `SUPPORTS` and `CONTRADICTS` relationships for evidence records with status `NO_GRANULES_IN_TARGET_INTERVAL` or `NO_SPATIOTEMPORALLY_SUITABLE_STATION`.

## Rationale

These statuses describe the result of a bounded source-availability screen. They establish that the searched route did not return a suitable observation within its declared scope; they do not measure the physical process represented by a hypothesis. The records may remain linked as `LIMITS_INTERPRETATION` or `DOES_NOT_DISTINGUISH` where that accurately describes the investigation gap.

The active T024 ECOSTRESS and ISMN records are currently unlinked from hypothesis assessments, so no existing disposition changes. The guard prevents a later analyst-authored link from treating missing source coverage as physical support or contradiction.

## Scope

This is a deterministic contract rule based on two explicit source-availability states. It does not infer source quality from arbitrary prose, decide which catalog query is scientifically adequate, or claim that the physical hypotheses are true or false.

See [validation](../validation/non-directional-source-availability-guard-2026-11-09.md).
