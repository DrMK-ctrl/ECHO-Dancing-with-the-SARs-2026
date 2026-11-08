# Present the investigation assessment in a wide dialog

**Date:** 2026-11-08  
**Status:** Implemented and exercised in headless Firefox

## Context

The complete case assessment had been rendered inside the fixed-width evidence sidebar. At a 1440-pixel desktop viewport, the assessment received about 305 pixels of width while containing a long evidence summary, observation cards, acquisition chronology, six hypotheses, follow-up designs, source links, and analyst review controls. The screen could technically load the data but presented the main investigative workflow as a narrow, difficult-to-read strip.

## Decision

Open a case-linked assessment in a native modal dialog sized to the desktop viewport. Give the assessment its own vertical scroll area, use the available width for responsive observation, hypothesis, and follow-up cards, and keep a close action sticky at the top. Preserve the underlying case/map state and the same assessment loader, source checks, and scientific status labels.

This is a presentation change only. It does not edit assessments, measurement records, source relationships, QA results, or scientific dispositions.

## Verification

- The full software suite passed: **298 tests**.
- Python compilation and `git diff --check` passed.
- Headless Firefox opened the T163 assessment from the case action. At a 1440-pixel browser width, the dialog measured 1360 pixels wide with 1346 pixels of content and no horizontal overflow.
- After scrolling into the follow-up records, the close control remained at the dialog's top edge. Clicking it closed the modal.
- A screenshot of the scrolled investigation view is retained as [dialog interaction evidence](../validation/investigation-assessment-dialog-2026-11-08.png).

## Limits

The browser interaction and desktop rendering were checked. Mobile layout, keyboard-only review, and a detailed visual review of every section remain open. The case assessment remains analyst-authored and diagnostic; the layout change does not validate any scientific conclusion.
