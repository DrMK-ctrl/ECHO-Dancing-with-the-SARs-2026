# Temporal comparison-candidate selector validation

**Date:** 2026-11-07

**Result:** Browser interaction verified with catalog metadata; no radar processing performed

## Browser checks

Served the retained six-record Istanbul catalog response through ECHO's local read-only server without loading its case review, so all catalog-screened alternatives were available. Headless Firefox rendered three candidate pairs in the comparison selector. Selecting the second option changed the selected pair to 2026-10-07 → 2026-10-19 (12 days), updated the pair-role markers and map highlight, and displayed a toast that the choice remains a metadata candidate pending QA and pixel checks.

At a 500 CSS-pixel viewport, `document.documentElement.scrollWidth` and `clientWidth` both measured 488 pixels. The selector contained all three options and the chronology remained internally scrollable. A desktop rendering is retained as [`comparison-candidate-selector-2026-11-07.png`](comparison-candidate-selector-2026-11-07.png).

## Limits

The selector exposes only the candidates returned by the existing adjacent-acquisition catalog matcher for this bounded query. The fixture contains metadata, not SAR rasters. This check does not establish exhaustive coverage, event-relative baseline suitability, provider QA passage, pixel registration, common valid coverage, measured change, persistence, or event interpretation.
