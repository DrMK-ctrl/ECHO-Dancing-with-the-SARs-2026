# Operational stability browser pass — 2026-11-12

**Scope:** Local interactive application, registered cases, geographic controls,
QA-held NISAR preview, pixel inspector, and investigation handoff.  
**Browser:** Firefox 158.0.1, fresh private headless profile.  
**Code baseline:** local `main`, HEAD `861eacd`; no source changes were retained
from this pass.

## Interaction results

- Loaded the Iraq case and switched through all six cases in the selector, then
  returned repeatedly to Iraq and the Rio Grande do Sul T163 investigation.
- Opened T163's case investigation and confirmed its diagnostic OPERA/Sentinel-1
  scope and unresolved assessment.
- Challenged the Iraq observation. ECHO stated that no change finding exists and
  held temporal interpretation because provider QA is `FAIL`.
- Used World View, zoom in/out, reset, and a browser pointer drag to draw a WGS84
  area. The map returned to the selected case after switching cases.
- Selected both Iraq timeline observations: 2026-10-08 (before) and 2026-10-20
  (after). Selecting the other acquisition cleared the prior single-scene preview.
- Loaded a genuine bounded NISAR GCOV HHHH measurement in the browser. The
  selected 2026-10-08 product was
  `NISAR_L2_PR_GCOV_032_122_D_070_2005_DHDH_A_20261008T160723_20261008T160758_P05023_N_F_J_001`.
  ECHO displayed 9,918 AOI pixel centers in EPSG:32637, the `10 log10(γ⁰)` display
  transform, product and acquisition identity, ASF QA `FAIL`, and the explicit
  diagnostic/no-change status. Its pixel inspector returned a selected pixel's
  γ⁰ value, dB display value, mask, number of looks, and exception code.
- Opened **Start investigation** from that preview. The form identified it as a
  single real NISAR observation, retained QA-held status, and stated that no
  hypothesis was evaluated. No draft was submitted or saved in this pass.
- A page-level error/rejection listener recorded no ECHO JavaScript errors during
  the valid interaction sequence.

## Retrieval latency observation

One browser read completed after approximately 132 seconds, while the interface
showed `READING WINDOW…`; the API remained responsive during the request. A
temporary 512 KiB read-ahead experiment requested 19,816,211 range bytes. It did
not establish a reliable speed improvement and transferred more bytes than the
prior 128 KiB run. The experiment was reverted; production preview reads retain
the existing 128 KiB setting. These were operational observations, not a
controlled benchmark. ASF response latency remains a known user-facing
limitation for live reads; the QA disposition and measurement values were not
altered to address it.

## Regression and cleanup

- Full automated suite after restoring the existing read configuration:
  `.venv/bin/python -m pytest -q` — **498 passed in 35.30s**.
- The temporary app server and WebDriver used for this pass were stopped. The
  previously running desktop demo and pre-existing local services were left
  unchanged.

## Acceptance limits

This pass covers Firefox on this Ubuntu workstation, not every browser, input
device, keyboard-only workflow, or assistive technology. It verifies one real
NISAR scene and its diagnostic handoff; it does not clear provider QA, establish
a temporal change, or validate a physical interpretation. Live retrieval timing
depends on the external ASF service and network path.

## Keyboard map panning follow-up

A fresh Firefox 158.0.1 WebDriver session against the existing loopback,
read-only Iraq application focused the interactive map and sent ArrowLeft,
ArrowRight, ArrowUp, and ArrowDown individually. Each event was received by the
map, had its browser default prevented, and caused the SVG map to rerender.
This verifies the map's documented four-direction keyboard panning. It does
not validate keyboard-only area drawing, catalog selection, every control's
focus order, or assistive-technology behavior.

## Source-linked challenge navigation follow-up

The map's general **Challenge this finding** control previously opened a
generic catalog-only prompt even when the current case had a recorded
investigation. It now opens the case investigation when one is available, or
the selected observation's QA-aware challenge when no case assessment is
available. The free-text prompt remains only as an explicitly unsaved fallback
when neither source-linked review is available; its copy no longer describes
the case as catalog metadata only.

The challenge review labels the SAR measurement and its reproduction as
case-linked measurement context, separate from the selected hypothesis under
review. This keeps a cross-sensor supporting statement from appearing to be the
SAR measurement itself.

Firefox 158.0.1 exercised the interaction against the local interactive app
with a temporary XDG draft-data directory:

- For Rio Grande do Sul T163, the control opened the retained case investigation
  with six hypothesis-specific challenge actions. Selecting H1 opened its
  deterministic source-linked review, which retained the descriptive-only
  disposition, diagnostic Sentinel-1/OPERA status, reproduced SAR measurement,
  evidence relationships, and QA limitations. No browser page errors occurred.
  The rendered review showed the case-measurement and reproduction labels after
  the distinction was clarified.
- For Iraq, the same control opened the QA-held observation challenge. It stated
  that no change finding exists, displayed the single-scene NISAR diagnostic
  observation and provider-QA `FAIL` on the 12-day metadata candidate, and kept
  temporal analysis on hold. No browser page errors occurred.

No assessment, draft, or evidence record was changed by this review. The
temporary app and browser processes were stopped afterward; existing demo
services were left running.

`.venv/bin/python -m pytest -q tests/test_investigation_renderer.py` — **8
passed in 0.58s** after the renderer terminology update.

A subsequent Firefox pass exercised the main challenge control against all six
registered cases. Iraq opened its QA-held no-change review; both Rio Grande do
Sul investigation cases exposed six hypothesis-specific challenge actions and
opened the linked challenge report; Istanbul, Mozambique, and Nepal opened the
explicit no-source-linked-finding prompt. There were no ECHO page errors. No
drafts or assessment records were submitted or changed.

That prompt now offers **Find observations** as a direct next step. A Firefox
check on the Istanbul case confirmed that it closes the prompt and opens the
catalog search dialog; it does not submit a provider request until the user
submits the search form. No browser page errors occurred.

## Malformed root URL recovery

The browser harness once supplied an empty case identifier and received a raw
JSON error page. The normal selector cannot produce that value, but an empty or
stale `/?case_id=` link should still open the configured default case. The root
route now falls back to that default only for an empty case identifier; API
requests remain fail-closed and return HTTP 400. A fresh Firefox 158 session
opened `/?case_id=` as the Iraq application with no page-level errors. The
case-registry regression test covers both root recovery and API rejection.

## Delayed NISAR preview response race follow-up

Review of the live-preview interaction identified a concurrency defect: a
bounded GCOV read can take over a minute, during which a user can select another
acquisition or area. The late response previously had no check that its scene
and request settings still matched the active map, so it could replace the
current measurement context with data requested for the prior selection.

`echo/static/app.js` now snapshots the case, scene ID, WGS84 bounds, frequency,
and layer for each preview request. It discards a response if the request is no
longer current or its inputs have changed. Changing the selected acquisition,
comparison pair, AOI, catalog search, or starting pair analysis invalidates a
pending read. A stale response also cannot reset controls belonging to a newer
request.

Firefox 158.0.1 exercised the actual application page on the Iraq case. The
browser test used a deliberately delayed, mocked preview response, switched
from the Oct 8 scene to Oct 20 while it was pending, and then released the
mock. ECHO retained Oct 20, displayed no preview inspector, and cleared the old
busy state. The mock was discarded before rendering; it was not satellite data
and did not exercise or alter the scientific measurement pipeline.

Regression verification after the fix:

- `.venv/bin/python -m pytest -q` — **498 passed in 35.48s**.
- `tests/test_web.py::test_local_interface_serves_static_app_and_read_only_catalog`
  — **1 passed in 0.69s**.
- `git diff --check` — clean.

The race pass validates scene-switch handling with a controlled delayed
response. It does not benchmark ASF or establish retrieval performance. The
existing Iraq and T163 services were left running and unchanged.

## Arbitrary global AOI selection follow-up

Firefox 158.0.1 used the map's World View, **Select Area**, and real pointer-drag
interaction to draw rectangles at three locations not tied to the loaded case:
Tehran, Iran; Maputo, Mozambique; and Tashkent, Uzbekistan. Opening catalog
search showed the selected WGS84 rectangle in the query form for each location:

- Tehran: `[50.0003, 34.8499, 52.4593, 36.4892]`
- Maputo: `[31.1477, -27.4455, 33.6067, -24.9865]`
- Tashkent: `[68.0331, 39.7679, 70.4922, 42.2270]`

This verifies global map navigation, arbitrary rectangle selection, coordinate
ordering, and handoff of the selected AOI into the catalog-search interface at
multiple longitudes and in both hemispheres. The catalog form was opened but no
provider search was submitted in this check, so it does not establish that
observations are available for these windows or test downstream raster
retrieval for them.

Separate loopback API calls then submitted those three returned WGS84 bounds to
ASF's GCOV catalog for 2026-10-01 through 2026-11-12 at `PROVISIONAL` maturity.
The service returned HTTP 200 with 22 Tehran, 18 Maputo, and 26 Tashkent
metadata records. These were catalog-only results; they did not retrieve QA or
pixels. A later, narrower Tehran search through the browser form returned six
records and proceeded to the bounded single-observation preview documented in
[`tehran-nisar-gcov-diagnostic-preview-2026-11-12.md`](tehran-nisar-gcov-diagnostic-preview-2026-11-12.md).

## Map control wrapping at desktop and laptop widths

A 1600px Firefox viewport exposed horizontal overflow in the map action row:
the wrapping breakpoint had been based on the browser width, although the
three-column workspace left the map panel only about 1024px wide. The stylesheet
now applies the wrapping rule to the map panel's own inline size.

Firefox 158.0.1 loaded the local application at 1600x1000 and 1366x900. At both
sizes, the map action row and secondary control row had equal client and scroll
widths (1022/1022 and 1002/1002 at 1600; 788/788 and 768/768 at 1366), with the
controls wrapping inside the map panel. A visual screenshot at 1600px confirmed
that the map controls remained legible and did not overlap adjacent panels.

## Responsive layout follow-up

Extending the same Firefox pass to narrower widths exposed two additional
issues: the case title and status/actions competed for the same narrow row, and
the catalog-search button inherited the generic 14px map-button font, clipping
its label. The mobile case heading now stacks its content and actions; the
intermediate desktop/tablet range stacks them when the main column is narrow;
the search button now retains its intended compact monospace font.

Firefox 158.0.1 exercised the actual app at CSS viewport widths 1600, 1366,
1200, 1024, 768, and 500px. At 1200px and below, the heading content and action
row occupy separate vertical positions; at 1366px and 1600px they remain
side-by-side without intersecting. At each width, map control `scrollWidth`
matched its `clientWidth`. At 500px, the search button text also fit its own
87px client width, and the document had no horizontal overflow. Visual review
of the 500px capture confirmed the title, case selector, case action, map
controls, and map warning remained separated and readable. The screenshot is
[`echo-mobile-layout-500px-2026-11-12.png`](assets/echo-mobile-layout-500px-2026-11-12.png).

Firefox would not create a CSS viewport narrower than 500px in this headless
environment, so narrower phone widths were not verified. This pass covers
responsive layout and visual separation; it does not validate every modal,
timeline interaction, keyboard focus sequence, or assistive technology at each
viewport size.

The 500px browser check also opened and closed **Find NISAR observations**.
The ASF catalog dialog occupied 456×467px within the viewport; its area-search
button remained inside the dialog. The search was not submitted because this
service is the curated read-only demo, where provider actions are intentionally
rejected. This verifies dialog presentation and close behavior, not a live
mobile catalog request.

At the same viewport, a touch-pointer drag across the map selected
`[-51.2375, -30.0378, -51.2331, -30.0324]` in WGS84 order. Opening the catalog
dialog carried those exact bounds into its selected-area summary. No provider
request was submitted. This exercises mobile-sized area selection and handoff
into observation discovery, not downstream raster retrieval.

## Adversarial challenge to map transition

The source-linked H2 water-change challenge exposed a modal-navigation defect:
**Show this diagnostic layer** closed the challenge dialog while leaving the
case investigation dialog open over the geographic workspace. The map state
changed underneath that modal, making the selected layer inaccessible. The
transition now closes the parent assessment modal as it switches to the map.

Firefox 158.0.1 exercised the retained T163 diagnostic case at a 500px CSS
viewport: open the case investigation, challenge H2, show its linked spatial
layer, change the display from SAR to DSWx water fraction, set common optical
support to 75%, then return to the case map. Both dialogs closed on transition.
The map showed 826 of 1,254 retained cells at the 50% default and 738 cells at
75%; the displayed count matched the deterministic support filter. The UI kept
the `DIAGNOSTIC EVIDENCE LAYER` warning, stated Sentinel-1-derived OPERA QA was
unresolved, and labeled the water-fraction layer and WGS84 attribution. Returning
to the case map restored its diagnostic OPERA comparison warning and hid the
challenge controls. No assessment or source record was modified.

Screenshot: [`echo-adversarial-map-mobile-500px-2026-11-12.png`](assets/echo-adversarial-map-mobile-500px-2026-11-12.png). This is a retained diagnostic comparison, not NISAR, a validated flood boundary, or a causal conclusion. The browser used the local curated read-only service and made no provider request.
