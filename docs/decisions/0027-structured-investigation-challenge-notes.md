# Decision 0027: Record human challenges against explicit hypotheses

**Date:** 2026-11-08
**Status:** Implemented as exportable, session-only review notes

## Context

The interface showed prepared hypothesis assessments and had a generic reflection prompt, but the prompt was not linked to a particular explanation or its source evidence. A reviewer could notice a contradiction, alternative mechanism, missing observation, or methodological limitation without a structured way to preserve that challenge for later reassessment.

## Decision

- Add a challenge action to each hypothesis in the linked assessment.
- Capture a challenge category, reviewer statement, proposed discriminating test, and optional reference to a linked evidence artifact. An explicit missing-source choice records an information gap.
- Export notes as a JSON record containing the case, assessment SHA-256 when browser Web Crypto is available, source artifact identifiers and hashes, target hypothesis, and a creation timestamp.
- Label each note `UNASSESSED_HUMAN_INPUT`; notes remain in page memory until export and do not alter evidence relationships, hypothesis dispositions, or scientific results.
- Keep this feature as a human review mechanism. It neither validates the challenge nor ranks follow-up observations.

## Verification

- Firefox exercised the T163 assessment, opened hypothesis challenges, and recorded both a missing-evidence note and a source-linked possible contradiction with proposed tests.
- The browser-rendered note remained explicitly unassessed, exposed the export action, and left the causal assessment unresolved.
- Intercepting the download verified both notes, the JSON record type, note statuses, hypothesis links, source linkage and checksum, filename, and 64-character assessment digests.

## Limits

Challenge notes are not persisted automatically and are not merged into the case assessment. A reviewer must export and later evaluate them against suitable evidence. This workflow does not demonstrate that ECHO autonomously identifies or resolves competing explanations.
