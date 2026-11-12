# Curated Iraq NISAR preview — 2026-11-12

## Result

The loopback `--read-only-demo` workspace now draws the case's previously retrieved, checksummed NISAR L2 GCOV HHHH measurement on first load. It is labeled as a retained local diagnostic record; the interface does not retrieve a new ASF measurement. Provider QA remains `FAIL`, the preview remains `QA_HELD_DIAGNOSTIC_PREVIEW`, and no temporal change result is computed.

The case record contains 9,918 selected pixel centers from the 2026-10-20 acquisition. The map applies the documented display transform to the product's linear gamma-zero power values. The observation inspector retains product identity, acquisition time, QA summary, mask counts, grid, and source checksums.

## Verification

- Headless Firefox opened the curated Iraq case and rendered the NISAR raster in the map SVG.
- Browser inspection confirmed the retained-record notice, `PROVIDER QA FAIL`, `QA-HELD DIAGNOSTIC PREVIEW`, 9,918 AOI centers, and the disabled `RETAINED DIAGNOSTIC PREVIEW` control.
- The server serves the retained record only after case identity, linked path, checksum, catalog scene, diagnostic disposition, and provider QA hold checks pass. Missing records return an explicit service error; stale checksums are rejected.
- The existing read-only tests still verify that POST operations remain blocked. Focused checks: 3 passed. Full suite: 465 passed. Python compilation and `git diff --check` passed.

Browser capture: [Iraq curated read-only preview](assets/iraq-curated-readonly-retained-preview-2026-11-12.png).

## Limits

This is one fixed, QA-held acquisition window in the retained Iraq case. It demonstrates authentic measurement display and provenance in read-only mode; it does not validate the provider product, establish temporal change, or support a physical event interpretation. Optional NASA GIBS imagery may still require internet access. The screenshot is an interface record, not scientific validation.
