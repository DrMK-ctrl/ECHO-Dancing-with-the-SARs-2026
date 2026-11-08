# Investigation assessment dialog validation

**Date:** 2026-11-08  
**Result:** Passed desktop runtime interaction and layout checks

## Procedure

Started the local ECHO server on loopback with the T163 case as the default, opened it in an isolated headless Firefox session, and activated **Open Case Investigation**. The browser loaded the case-linked assessment and rendered its measurement summary, chronology, hypothesis cards, follow-up designs, and source-inspection controls in a native modal dialog.

## Observations

- Browser content viewport: 1440 × 914 CSS pixels.
- Dialog bounding size: 1360 × 882 pixels; inner content width: 1346 pixels.
- Dialog scroll width equaled client width (1346 pixels); no horizontal overflow was present.
- At scroll position 2600 pixels, the sticky toolbar remained visible near the dialog's top edge. The user could close the dialog from that position, and Firefox reported the dialog closed.
- The screen retained the explicit unresolved causal disposition and diagnostic Sentinel-1/OPERA source label.
- Screenshot: [scrolled assessment and sticky toolbar](investigation-assessment-dialog-2026-11-08.png).

## Verification

- Full test suite: **298 passed**.
- `python3 -m compileall -q echo`: passed.
- `git diff --check`: passed.

## Limits

This verifies one desktop viewport and a normal pointer interaction. It does not validate mobile layout, keyboard-only navigation, every evidence inspector action, scientific correctness of the authored relationships, or any causal interpretation. The dialog presents the existing diagnostic assessment; it does not upgrade its evidence status.
