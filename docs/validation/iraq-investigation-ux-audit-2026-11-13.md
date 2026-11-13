# Iraq investigation workflow audit — Firefox

**Date:** 2026-11-13

**Surface:** interactive local ECHO workbench at `127.0.0.1:8766`

**Browser / viewport:** Firefox headless, 1366 × 1000 CSS pixels

**Network:** external HTTP and HTTPS routed to an unreachable local proxy; map backdrop set to `OFF`

## User goal

Open the Iraq NISAR case, understand which observation is available, inspect why
temporal analysis is held, and deliberately challenge the interpretation.

No ASF measurement request, draft mutation, or scientific recalculation was
made. The challenge panel read the retained local case and QA records.

## Steps and findings

1. **Open the Iraq case — health: corrected.** The first capture showed the
   October 8 `PAIR · BEFORE` scene selected while the case's retained
   single-scene preview and challenge target were from October 20. The map
   correctly said `NO RADAR PIXELS LOADED`; the sidebar disclosed that an
   October 20 preview exists, and `LOAD BACKSCATTER` was available. This was a
   context mismatch: the selected-scene metadata and the challenge subject
   referred to different acquisitions. The initial screen is
   [`01-investigation-workspace.png`](assets/product-ux-iraq-2026-11-13/01-investigation-workspace.png).

2. **Open “Challenge this observation” — health: scientifically sound, with
   the same context mismatch.** The panel stated that no change finding exists
   to challenge; it identified the 20 October measurement, source hash, QA
   status for both products, and the absence of temporal analysis or a physical
   explanation. The long product IDs and hashes are dense at this viewport, but
   remain available beside clear QA and assessment headings. The underlying
   timeline still showed October 8. See
   [`02-challenge-observation.png`](assets/product-ux-iraq-2026-11-13/02-challenge-observation.png).

3. **Reopen after the selection fix — health: coherent.** When a case has a
   retained diagnostic preview, startup now selects that preview's scene if it
   exists in the catalog. The timeline and metadata panel both showed the
   October 20 `PAIR · AFTER` acquisition. The geographic map still said no
   pixels were loaded, which is accurate until the user requests a preview.
   Provider QA remained `FAIL`. See
   [`03-workspace-aligned.png`](assets/product-ux-iraq-2026-11-13/03-workspace-aligned.png).

4. **Challenge the aligned observation — health: coherent and fail-closed.**
   The selected October 20 scene matched the challenge's acquisition timestamp.
   The panel retained `QA_HELD`, reported that no temporal change was computed,
   and made no physical-cause conclusion. See
   [`04-challenge-aligned.png`](assets/product-ux-iraq-2026-11-13/04-challenge-aligned.png).

## Change and verification

`renderWorkspace()` now prefers the case's recorded diagnostic-preview scene
when it must choose an initial selection. Cases without that preview retain the
existing metadata-pair `BEFORE` default. The focused Python regression passed
and a real Firefox run verified that the Iraq timeline, observation details,
and challenge report all identify the October 20 product. A second Firefox run
verified that Nepal, which has no retained single-scene preview, still opens
with its `PAIR · BEFORE` observation selected.

This audit covers one QA-held NISAR case and one no-preview pair-selection
regression. It does not validate the measurement read itself, full keyboard tab
order, screen-reader behavior, or the entire interface. Both Iraq products
remain provider-QA failed; no change conclusion was produced.
