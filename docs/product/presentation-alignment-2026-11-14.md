# ECHO product narrative alignment — 2026-11-14

## Product frame

The seven-slide judge presentation names ECHO the **SAR Change Evidence Engine** and sets its promise as: “The radar sees a change. ECHO tests what it means.” The application now uses that exact product name in its browser title and workspace footer. ECHO remains the Earth Change Observatory; the engine name describes the product role.

The presentation's core flow is **Locate → Compare → Inspect → Explain**. The workspace supports that story through geographic context and area selection, acquisition timeline/pair selection, source-linked measurements and product QA, and competing-hypothesis/evidence review. The slides' Rio Grande do Sul/T163 view is explicitly labeled a workflow schematic; do not present its map texture or timeline as a case result.

## Judge case and scientific boundary

The presentation explicitly identifies the Iraq NISAR pair as QA-held and diagnostic. The judge walkthrough should open the curated, single-case Iraq mode:

```bash
.venv/bin/echo serve --read-only-demo \
  --case-file data/cases/iraq-2026-nisar-diagnostic/catalog.json
```

The retained October 8/20 candidate pair has provider QA `FAIL` on both products. ECHO stops before pair measurement reads and computes no change statistic. The map's retained October 20 HHHH raster is a **single-scene diagnostic preview**, not the pair result; its source, date, layer, QA state, and preview boundary remain visible. This distinction matches the deck's QA slide and its unresolved-outcome definition.

The app's assessment dispositions are `SUPPORTED_WITHIN_SCOPE`, `CONTRADICTED_WITHIN_SCOPE`, and `UNRESOLVED`. The scope qualifier keeps those labels attached to a tested hypothesis and its evidence, rather than implying calibrated detection confidence or physical causation. The Iraq case remains unresolved because its pair has not passed QA.

## Supporting capabilities

The optional AI Investigator is not part of the seven-slide core pitch. It is user-directed local assistance for organizing cited case evidence and proposing checks. In curated mode it remains available and can save a separate AI-authored run under the local XDG data directory, outside the case bundle. Its output is a draft; it cannot change measurements, QA status, or assessments. The curated-mode banner and demo description should say that provider retrieval, SAR analysis, and case-draft mutation are blocked, while this separate AI draft remains possible. Keep it secondary in judge narration, and never use it to imply the held Iraq pair has a change result.

## Verification

- Extracted and reviewed all seven slides and embedded speaker notes from the supplied presentation. Slide 4 marks its map/timeline as schematic; slide 6 states the Iraq pair's QA hold; slide 7 defines the three outcome classes.
- Started the curated Iraq server on an isolated loopback port and confirmed its registry contains only `iraq-2026-nisar-gcov-diagnostic`.
- Firefox challenge-flow check passed: it displayed “No change finding exists to challenge,” the pair QA gate and `FAIL`, and “No temporal change was computed.” It made one local GET and reported no page errors.
- Full automated suite on the current working tree: **565 passed in 43.73 seconds**.

This note records narrative alignment, not scientific validation of a NISAR change result. The provider QA failure remains decisive.
