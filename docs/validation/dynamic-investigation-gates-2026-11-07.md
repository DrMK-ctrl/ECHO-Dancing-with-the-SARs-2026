# Dynamic investigation gate rendering

**Validated:** 2026-11-07
**Scope:** Case-specific evidence panel and gate states in the local Firefox interface.

## Change

The evidence panel previously retained static QA and alignment copy whenever a case review file was loaded. The readiness statement also assumed every review represented a QA-held pair. ECHO now derives catalog, provider-QA, pixel-comparison, and independent-evidence states from the selected pair, retained review, and current analysis result. The initial HTML shell uses loading text, so it does not briefly present another case's name or QA result before the local records load.

## Browser evidence

Started the local interface against the retained Istanbul and Mozambique catalog files and inspected the rendered DOM in headless Firefox after each workspace loaded.

- **Istanbul:** the selected 12-day PROVISIONAL pair appeared as a metadata candidate; both retained provider summaries displayed `FAIL`; pixel comparison remained open; the independent/context record was explicitly described as not independently assessed.
- **Mozambique:** the selected 12-day BETA pair appeared as a metadata candidate; both retained provider summaries displayed `FAIL`; pixel comparison remained open; no independent reference assessment was recorded.
- Both showed `1 OF 4 GATES · QA HOLD`, with catalog candidacy, QA, pixel-grid, and interpretation states rendered from their own case records.
- The page loaded successfully and the browser session was closed after inspection.

This validation used retained case metadata and did not retrieve new products, read raster pixels, run pair analysis, or change any provider QA disposition. The display therefore remains a workflow/readiness view, not a scientific comparison or finding.

## Verification limits

The browser check covered the two retained review schemas and their QA-held pairs. A live QA-PASS pair and a measured real-data comparison remain unavailable; the passed and measured visual states are not accepted by this evidence.
