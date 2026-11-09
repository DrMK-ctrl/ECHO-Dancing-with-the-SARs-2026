# Decision 0087: Surface open investigation decisions

**Date:** 2026-11-09  
**Status:** Implemented and browser-verified

## Context

The investigation view showed follow-up actions as a list and explicitly avoided ranking them. That preserved uncertainty but left users to infer which recorded dependencies block interpretation and which evidence searches remain open.

## Decision

Derive a small decision summary from the assessment's existing unresolved hypothesis states, follow-up action tracks, and availability states. Show active quality prerequisites in an interpretation-gate section and active evidence searches in a separate section. Keep completed or quality-limited screens in the audit list.

Do not calculate numeric priority, confidence, probability, or expected information gain. Do not infer that a cataloged or proposed source is available or scientifically suitable. Do not mutate or extend the retained assessment record.

## Consequences and limits

- T163 presents provider-resolved RTC-S1 QA as an interpretation gate and the independent soil-moisture route as an open search for unresolved H3.
- A visible order reflects workflow dependency and declared state only; it is not a scientific value ranking.
- The open search retains previously screened routes and their limitations, reducing the chance of repeating unavailable queries unchanged.
- The recommendation remains analyst-authored at the source-record level. This UI summary does not autonomously discover observations or assess their scientific suitability.

## Validation

See [investigation next-decision browser validation](../validation/investigation-next-decision-summary-2026-11-09.md) and its [browser capture](../validation/investigation-next-decision-browser-2026-11-09.png).
