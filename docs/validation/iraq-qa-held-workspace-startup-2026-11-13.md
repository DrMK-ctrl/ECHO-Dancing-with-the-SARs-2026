# QA-held Iraq workspace startup and challenge review — Firefox, 2026-11-13

## Scope

Firefox 158.0.1 opened ECHO's local, curated read-only Iraq NISAR case at a
1366 × 814 CSS-pixel viewport. The case uses its retained, checksummed, authentic
single-scene GCOV preview. No provider request, new measurement read, or draft
mutation was made during this walkthrough.

## Steps and results

1. **Open the Iraq case.** The initial browser capture showed the timeline's
   selected observation had moved the whole document down by 195.8 CSS pixels:
   the top bar was above the viewport and the case title was clipped. The
   QA-held preview and its provider `FAIL` status were otherwise present. See
   [the initial capture](assets/iraq-qa-held-initial-scroll-before-fix-2026-11-13.png).

2. **Reload after the fix.** The initial document remained at `scrollY = 0`,
   the top bar began at viewport coordinate 0, and the case title began at
   `y = 175.5`. The real backscatter raster was visibly overlaid on the selected
   WGS84 area; the map labeled it `QA-HELD REAL SAR PREVIEW` and stated that
   provider QA failed and no change result exists. The case panel retained the
   acquisition identity and pair QA hold. See [the corrected initial view](assets/iraq-qa-held-initial-workspace-2026-11-13.png).

3. **Challenge the observation.** Selecting **Challenge this observation**
   opened a source-linked review headed **No change finding exists to
   challenge**. It showed the measurement layer, acquisition time, source hash,
   candidate interval, both provider QA failures, and the limit that no temporal
   change or physical explanation was computed. The dialog did not scroll the
   document. Its long evidence list remains internally scrollable. See [the
   challenge view](assets/iraq-qa-held-observation-challenge-2026-11-13.png).

## Root cause and correction

`renderWorkspace()` calls `renderTimeline()` during startup. The selected
observation row previously called `scrollIntoView({block: "nearest"})`, which
also scrolled the outer document to expose the timeline. `renderTimeline()` now
centers the selected row by changing only the horizontal timeline scroller's
`scrollLeft` value. This preserves the page's initial top position while
retaining timeline selection behavior.

## Verification

- Firefox 158.0.1: initial viewport, retained raster, QA state, and observation
  challenge verified in a real browser.
- Firefox also exercised timeline alignment with a **synthetic UI-only fixture**
  containing 12 ordered entries and the selected pair at entries 11–12. The
  selected row was brought into view horizontally (`scrollLeft = 1574`) while
  `window.scrollY` stayed at 0. These fixture entries are not satellite data.
- Focused regressions: **2 passed** (workspace static-serving contract and
  horizontal timeline scroll behavior).
- Full suite: `.venv/bin/python -m pytest -q` — **508 passed in 33.41 seconds**.

## Limits

This is a focused startup and challenge-flow check in the curated read-only
Iraq case, not a complete accessibility or all-controls audit. It does not
change the retained provider QA `FAIL`, establish a valid temporal comparison,
or support an event or causal conclusion.
