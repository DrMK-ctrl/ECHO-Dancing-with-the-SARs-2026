# Decision 0111: Challenge saved, assessed investigation drafts

**Date:** 2026-11-12
**Status:** Accepted

## Context

ECHO's retained case assessments exposed the adversarial challenge workflow, but analyst-authored investigations could not use it. The draft interface deliberately hid the action for every draft. This left the evolving workflow disconnected at the point where users should inspect competing explanations and evidence gaps.

## Decision

Expose **Challenge This Finding** for each hypothesis only after an analyst-assessed draft has been saved as an immutable local snapshot. The local API loads the content-addressed snapshot, checks its integrity and active case links, and assembles a dossier from the selected hypothesis and its recorded source relationships.

The dossier reports linked and unassessed sources, recorded alternatives, registered follow-up observations, and fields present in the primary source's measurement object. It does not recompute measurements or sensitivity, authenticate analyst input, judge source independence, alter the saved draft, or change provider QA. It marks these limits in the response and interface.

## Consequences

- The challenge action is available inside the existing investigation and evidence-inspection flow.
- Unassessed and unsaved drafts cannot be challenged through this path.
- QA-held and diagnostic sources keep their recorded status and remain non-directional under the existing draft assessment contract.
- This is a reproducible review of analyst-recorded material, not a scientific validation result or a replacement for the case-specific challenge adapters.
