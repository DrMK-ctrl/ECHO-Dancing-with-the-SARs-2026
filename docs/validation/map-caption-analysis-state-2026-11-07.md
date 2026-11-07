# Map caption and analysis-state synchronization

**Date:** 2026-11-07  
**Result:** Firefox headless checks passed  
**Scope:** UI state synchronization only

## Product-maturity hold

A temporary copy of the Istanbul catalog was used to exercise a BETA pair. The browser submitted the pair through the normal workspace control to a local test route that returned a mocked `MATURITY_HELD` record with provider QA marked `PASS`. The interface showed:

- `Selected pair · product maturity held · no comparison pixels read` in the map caption;
- the product-maturity hold warning and `NO MEASUREMENT LAYER` attribution;
- an evidence inspector with `measurement arrays: NOT_READ` and `change calculation: NOT_PERFORMED`.

The catalog copy and API response were test fixtures. No BETA provider product or measurement arrays were accessed.

## Retained NISAR preview

A separate browser check selected the scene in [`real-gcov-window-preview-2026-11-07.json`](../../data/research/real-gcov-window-preview-2026-11-07.json) and loaded that retained response through a local mocked endpoint. The map caption changed to `NISAR HHHH backscatter preview · product QA FAIL`; the warning remained `QA-HELD REAL SAR PREVIEW · Provider QA FAIL · no change result`, and the attribution named NISAR GCOV HHHH with the NASA GIBS context boundary.

This replays a checksummed record from the earlier live NISAR API run. It is not a new network retrieval, pixel calculation, or scientific validation.

## Defect corrected

Before this change, `drawMap()` updated the QA warning, attribution, and raster but left the caption at its previous metadata-only text. Caption rendering now runs whenever the map redraws, keeping the visible map state synchronized after pair analysis, single-scene preview, and observation selection.

The browser checks validate interface presentation. They do not validate provider QA, product maturity, scientific suitability, or temporal change.
