# Decision 0102: Reproduce and version investigation assessment rebuilds

**Date:** 2026-11-09
**Status:** Implemented for the cross-sensor investigation builder

## Context

The documented T163 rebuild had been compared with its retained assessment after excluding `created_at_utc`. A fresh run against the current builder showed additional differences in observation summaries and follow-up evidence links, while the six hypothesis dispositions and overall unresolved status remained unchanged. The assessment record therefore needed a versioned refresh, and the rebuild command needed a stable, explicit timestamp option so the same code and source set can reproduce the same serialized record.

## Decision

Allow `build_cross_sensor_investigation.py` to accept an optional timezone-aware `--created-at-utc` value. Without it, the builder records the actual current UTC time. With it, the builder normalizes the supplied instant to UTC and rejects naive datetimes. The retained assessment's timestamp can be supplied when reproducing that exact version; a new assessment revision uses its actual build time.

Refresh the active T163 case to a new, versioned assessment file and update its case manifest. Keep the previous assessment file intact. Validate all linked source records and record any changed summaries or follow-up references without promoting their evidence status or changing hypothesis dispositions.

## Consequences

- A build with identical source records, code, environment, and explicit timestamp can be compared byte-for-byte.
- Build time remains truthful by default; reproductions of earlier versions can explicitly use their retained timestamp.
- The T163 case keeps its prior assessment as a separate retained artifact, while the active case points to the refreshed record.
- This refresh summarizes retained source records. It does not create a new satellite measurement, clear OPERA QA, or resolve causal interpretation.

See [validation](../validation/investigation-assessment-rebuild-reproducibility-2026-11-09.md).
