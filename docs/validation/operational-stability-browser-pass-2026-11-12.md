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

## Malformed root URL recovery

The browser harness once supplied an empty case identifier and received a raw
JSON error page. The normal selector cannot produce that value, but an empty or
stale `/?case_id=` link should still open the configured default case. The root
route now falls back to that default only for an empty case identifier; API
requests remain fail-closed and return HTTP 400. A fresh Firefox 158 session
opened `/?case_id=` as the Iraq application with no page-level errors. The
case-registry regression test covers both root recovery and API rejection.
