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
