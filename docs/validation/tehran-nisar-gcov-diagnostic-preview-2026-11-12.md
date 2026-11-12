# Tehran arbitrary-area NISAR GCOV preview — 2026-11-12

**Disposition:** real single-observation preview retrieved and rendered; provider QA `FAIL`; diagnostic only.

## Browser workflow

Firefox 158.0.1 used the interactive local application to navigate to Tehran,
draw and refine an arbitrary WGS84 area, search ASF GCOV metadata for
2026-10-01 through 2026-11-12 at `PROVISIONAL` maturity, and select an acquired
scene. The refined search returned six catalog records. The application then
retrieved and drew a bounded NISAR measurement through its **Load Backscatter**
control; no complete product download was requested.

The selected product is NISAR L2 GCOV, scene
`NISAR_L2_PR_GCOV_033_136_D_071_2005_DHDH_A_20261021T152620_20261021T152655_P05023_N_F_J_001`,
acquired 2026-10-21 15:26:20–15:26:55 UTC. The source is the ASF DAAC
[NISAR product](https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_PROVISIONAL_V1/NISAR_L2_PR_GCOV_033_136_D_071_2005_DHDH_A_20261021T152620_20261021T152655_P05023_N_F_J_001/NISAR_L2_PR_GCOV_033_136_D_071_2005_DHDH_A_20261021T152620_20261021T152655_P05023_N_F_J_001.h5).

The selected AOI was `[51.22582234648001, 35.72020762961902,
51.23391088020262, 35.72783656159433]` (west, south, east, north). The app
streamed 9,084,165 bytes by HTTPS range requests and displayed 1,554 pixel
centers from a 37 × 42 window in EPSG:32639. The raw measurement is frequency A,
HHHH linear gamma-zero power. The map's `10 log10(γ⁰)` and percentile stretch
are display transforms only. The preview retains per-pixel mask, number-of-looks,
exception, coordinate, and checksum records.

## QA and scientific boundary

The ASF QA summary returned `FAIL` on the identification-group check. Its
remaining listed checks returned `PASS`, but ECHO retains the provider-level
`FAIL`; the summary does not attribute the identification failure to a
specific field. The system therefore labels the layer **QA-held diagnostic
preview**. It reports one measurement only: there is no temporal change result,
event interpretation, or physical cause assessment.

The provider QA CSV reference and SHA-256 are retained inside the preview
record. The original CSV itself is not bundled. This preview does not clear the
Iraq or other product QA holds and is not an accepted analytical result.

## UI consistency fix

The real browser retrieval exposed a state mismatch: the preview inspector
showed ASF `FAIL`, while the selected observation details still said `NOT
REVIEWED`. After confirming the preview response belongs to the current scene,
`echo/static/app.js` now places that exact returned provider QA summary in the
selected-scene QA cache before rendering. The QA summary is not applied if the
response scene ID does not match the active acquisition.

The patched interface was checked in Firefox using a replay of the exact
authentic preview record captured during the live browser retrieval. This
avoided another remote range read. The selected observation then displayed QA
`FAIL`, the map showed the measured raster, the inspector retained the
QA-held/no-change wording, and the old “READING WINDOW…” state cleared. The
replay verifies rendering and state propagation; it is not a second acquisition
or a new measurement.

The same QA-cache update is applied after pair analysis. A live Firefox check
ran **Analyze Pair** on the Iraq October 8/20 candidate against ASF. Both
returned summaries were `FAIL`; the application displayed `QA_HELD`, reported
`measurement_arrays: NOT_READ` and `change_calculation: NOT_PERFORMED`, drew no
pair raster, and showed `FAIL` in the selected-scene details. No page errors
occurred. This was a real provider QA check, not a synthetic or cached pair
result.

Screenshot: [Tehran diagnostic preview in the map workspace](tehran-nisar-gcov-browser-preview-2026-11-12.png).

## Reproducible artifacts and checks

- Exact response: [`data/research/tehran-nisar-gcov-diagnostic-preview-2026-11-12.json`](../../data/research/tehran-nisar-gcov-diagnostic-preview-2026-11-12.json)
- Response-file SHA-256: `16dc1b97cc0c3f7b245dac3a9cb0bf95aee2dca4a70b3bb80a6ed58f3526484e`
- Live Iraq pair gate response: [`data/research/iraq-live-gcov-pair-qa-held-2026-11-12.json`](../../data/research/iraq-live-gcov-pair-qa-held-2026-11-12.json), SHA-256 `3d7679ca688c3b3119780c42e19290ae71ec62f5236f9b8d45bad18be4f799b2`
- Firefox 158.0.1 live app workflow: area selection, ASF metadata search, selected acquisition, real bounded read, map raster and preview inspector — passed.
- Firefox patched-render check: real preview-record replay displayed QA `FAIL` consistently in the observation details and preview inspector — passed.
- `.venv/bin/python -m pytest -q` — **498 passed in 33.77s** after the QA-state synchronization change.

This establishes that ECHO can connect an arbitrary user-selected region to
real NISAR metadata and a quantitative, geographically positioned diagnostic
measurement. It does not establish QA-cleared science or prove that every
geographic region has available NISAR coverage.
