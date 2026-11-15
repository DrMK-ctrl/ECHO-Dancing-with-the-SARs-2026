# Current-source browser regression — 2026-11-13

This record preserves real Firefox screenshots and browser-check results from the current local checkout. The screenshots are unaltered PNG captures. The replay server was bound to loopback (`127.0.0.1:8766`). No catalog query, credential submission, or investigation mutation was performed by the AOI interaction checks.

## Source snapshot

- Checkout: `/home/mahdi-kheirddine/Projects/echo-dancing-with-the-sars-2026`
- Branch: `main`
- HEAD: `2a13d8860309b4ad074ba69a7eaa9851a098cc63`
- Commit date: `2026-11-13T13:03:21+02:00`
- The working tree contains uncommitted changes. These checks exercised the current working source, not a clean checkout of HEAD.

## Browser checks

The local server was started with:

```sh
.venv/bin/echo serve --host 127.0.0.1 --port 8766
```

Current-source Beirut NISAR preview, requiring retained source-attribute hashes:

```sh
.venv/bin/python tools/validation/check_gcov_preview_browser.py \
  --require-source-attributes \
  --screenshot /tmp/echo-final-current-source.png
```

Result: **PASS, 10/10 checks.** The browser rendered the real raster and AOI bounds, exposed QA-fail and diagnostic-only status, supported real-pixel and source-record inspection, verified both retained product/quality attribute hashes, reported sample handling, used only local replay responses, and emitted no browser errors. The inspected pixel was row `12971`, column `5068`: gamma0 `30.9233` (linear), display value `14.90 dB`, mask `1`, looks `5.1905713`, exception mask `0`. The dB display is a visualization transformation; this one pixel is not a change result. Provider QA remains `FAIL`; the preview remains diagnostic and QA-held.

Legacy Hilo retained-preview compatibility:

```sh
.venv/bin/python tools/validation/check_gcov_preview_browser.py \
  --url 'http://127.0.0.1:8766/?case_id=iraq-2026-nisar-gcov-diagnostic' \
  --preview data/research/nisar-hawaii-hilo-gcov-diagnostic-preview-2026-11-10.json \
  --catalog data/research/validated-gcov-global-time-series-2026-11-10-13.json \
  --screenshot /tmp/echo-legacy-hilo.png
```

Result: **PASS for the baseline browser checks.** The older retained record has no source-attribute hashes. The harness reports `NOT_RECORDED_IN_RETAINED_PREVIEW`; it does not manufacture hashes or treat their absence as evidence of verification. The pixel displayed gamma0 `0.0692902` (linear), `-11.59 dB`, mask `1`, looks `5.3306589`, exception `768`. Provider QA is `FAIL`; this remains QA-held diagnostic data.

Global exploration and area-selection interaction:

```sh
.venv/bin/python tools/validation/check_map_area_browser.py \
  --url http://127.0.0.1:8766 \
  --screenshot /tmp/echo-final-global-aoi.png
```

Result: **PASS.** The application opened in global exploration without a selected case. The 360-degree map, WGS84 bounds form, pointer-drawn area, optional/closable Bhoonidhi dialog, and date controls were exercised. Pinch-in/out changed map span from 360 to 178.77 degrees and back, with the zoom anchor held within floating-point tolerance. Ordinary two-finger scrolling was not prevented, and a pinch during AOI draw mode was not intercepted. No catalog request was made.

Case-workbench area-selection interaction:

```sh
.venv/bin/python tools/validation/check_map_area_browser.py \
  --url 'http://127.0.0.1:8766/?case_id=iraq-2026-nisar-gcov-diagnostic' \
  --screenshot /tmp/echo-final-case-aoi.png
```

Result: **PASS.** WGS84 area selection and Escape behavior worked; selection controls behaved consistently; Bhoonidhi remained optional and closable; pinch anchoring, ordinary scroll, and AOI draw-mode behavior matched the global view. No provider request or investigation mutation occurred.

Current-checkout T024 challenge-to-map handoff:

```sh
.venv/bin/python tools/validation/check_t024_baseline_challenge_browser.py \
  --url 'http://127.0.0.1:8766/?case_id=rio-grande-do-sul-cross-sensor-diagnostic-2024'
```

Result: **PASS.** Firefox opened the retained Rio Grande do Sul evidence review, inspected the expanded temporal-baseline challenge, and followed the 408-day baseline to its corresponding map measurement. It retained series SHA-256 `191cac49a1718c3b5c0fd85d2c7ee814c37c484e8ba7462e92aa9cd2c1bae738`, comparison key `baseline:0`, and acquisition times `2024-05-11T08:49:47+00:00` to `2025-06-23T08:49:37+00:00`. The selected all-date common support was 1,034 of 1,199 AOI cells; the baseline median log-ratio was `-1.252 dB` over 408 days. There were no browser errors and only one local read-only challenge API request. The screen preserves OPERA's diagnostic status and does not establish causal interpretation or a validated event result.

The global exploration browser check was rerun against the same worktree:

```sh
.venv/bin/python tools/validation/check_map_area_browser.py \
  --url http://127.0.0.1:8766 \
  --screenshot /tmp/echo-goal-global-map-2026-11-13.png
```

Result: **PASS.** The default route remained a no-case global exploration view at 360 degrees; its only API read was `/api/cases`. Keyboard and pointer AOI selection, optional Bhoonidhi close/continue behavior, pinch zoom anchoring, ordinary scroll, and pinch during drawing passed. Catalog submissions were `0`; investigation mutations were `false`. Pinch-in reduced longitude span from 360 to `178.7707093649` degrees; pinch-out restored it to `359.99999999999966`. The zoom-anchor coordinate changed only at floating-point precision.

## Captures

| Capture | What it demonstrates |
|---|---|
| [Beirut current-source NISAR preview](assets/final-browser-regression-2026-11-13/01-beirut-current-source-preview.png) | A real single-acquisition NISAR GCOV raster preview, metadata and measurement inspection, plus explicit provider QA failure and diagnostic-only disposition. It does not demonstrate change detection. |
| [Hilo legacy preview compatibility](assets/final-browser-regression-2026-11-13/02-hilo-legacy-preview-compatibility.png) | Older retained preview still renders and remains QA-held. The old record lacks the newly retained source-attribute hashes. |
| [Global exploration AOI and pinch](assets/final-browser-regression-2026-11-13/03-global-exploration-aoi-and-pinch.png) | Global map entry and geographic/date search controls with a selected area. It does not show catalog results because the check intentionally made no provider request. |
| [Iraq case AOI and pinch](assets/final-browser-regression-2026-11-13/04-iraq-case-aoi-and-pinch.png) | AOI and gesture interactions within the saved Iraq case context. It does not change that case's QA-held scientific status. |

SHA-256:

```text
1a86e236257bdbd521185f7d4fb81f1e91fbed582ce442459b6ba15a657ce4af  01-beirut-current-source-preview.png
ca5e591de036fce34d0c3341c46cbebcd66e1ac57ae8fdb3bc1c76df2d8ecc6d  02-hilo-legacy-preview-compatibility.png
8971916f7bdfb2aa2fddf71a02ecfa6c27fd3071eafc888d2bc88950a1a7c8c1  03-global-exploration-aoi-and-pinch.png
848fdd7101e5efde8776ff02512e1e8b40d3318eb288c4109099277002bb6f37  04-iraq-case-aoi-and-pinch.png
```

## Interpretation and limits

These browser checks establish that the tested current-source interactions and retained preview paths work in the local browser session. They are not validation of provider QA, scientific correctness of the source product, geographic accuracy beyond the exercised UI checks, or evidence for a surface-change conclusion. The Beirut product's upstream QA failure remains a hard hold; one observation cannot establish temporal change. The Hilo record is a compatibility fixture with an incomplete retained-hash record. No code or data were changed by these browser runs.
