# Decision 0031: Separate quality prerequisites from evidence searches

**Date:** 2026-11-08
**Status:** Implemented for the two active Rio Grande diagnostic assessments

## Context

The assessment already retained follow-up actions, but the interface called them unranked and presented completed context retrieval beside open work. A single ranking would imply comparable value despite different purposes: provider QA determines whether a measurement can pass its quality gate, while a scientific observation may test a physical explanation and can be sought while QA is pending.

## Decision

Assign each follow-up a deterministic `action_track` from its declared purpose and availability:

- `QUALITY_PREREQUISITE` — a quality gate is unsearched or awaits a provider response.
- `NEW_EVIDENCE_SEARCH` — a discriminating observation is explicitly not searched.
- `REVIEWED_RESULT` — the referenced context or analysis has been retrieved or evaluated; it is retained for interpretation but is not presented as an open search.

Show these tracks together as the next investigation workstreams, explicitly stating that they are not a value ranking. A pending quality prerequisite does not prevent searching for scientifically relevant context, but all downstream conclusions remain subject to the quality gate.

## Current T163 result

- Provider-resolved RTC-S1 QA is an open quality prerequisite before accepting the radar measurement.
- Independent, scale- and time-appropriate surface-state evidence is the open scientific search for H3.
- The optical follow-up, area-weighted overlay, polarization sensitivity, and GPM precipitation context are already retrieved and assessed; their limitations remain visible.

No numeric information-gain score or AI ranking is claimed. The workstream class is a transparent workflow distinction, not an estimate of scientific value or outcome probability.
