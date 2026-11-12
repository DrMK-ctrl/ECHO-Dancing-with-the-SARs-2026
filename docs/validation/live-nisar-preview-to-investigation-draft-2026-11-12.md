# Live NISAR preview to investigation draft — 2026-11-12

## Result

In Firefox, a newly drawn Iraq sub-AOI was read from ASF as a bounded NISAR GCOV preview, displayed on the map, then passed directly from the preview inspector into ECHO's analyst-authored investigation form. The form created an unassessed draft while preserving the provider QA failure and the distinction between measurement and interpretation.

## Source and measurement

This browser run repeated the source/area from [the live arbitrary-AOI map check](live-arbitrary-aoi-nisar-map-preview-2026-11-12.md): bounds `[41.205, 36.705, 41.215, 36.715]` WGS84 and scene `NISAR_L2_PR_GCOV_033_122_D_070_2005_DHDH_A_20261020T160723_20261020T160758_P05023_N_F_J_001`. ECHO retrieved and rendered 2,476 real HHHH pixel centers. ASF QA returned `FAIL`; the UI retained `QA-HELD DIAGNOSTIC PREVIEW` and “no change result.”

## Investigation handoff

Selecting **START INVESTIGATION** opened the form with the source type `ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW`, status `QA_HELD_DIAGNOSTIC_PREVIEW`, and text stating that the acquisition is not a temporal change measurement, QA remains unchanged, and no hypothesis is evaluated in the draft.

The browser submitted two explicitly alternative explanations and one proposed independent optical follow-up. ECHO returned `DRAFT_NOT_ASSESSED`; the source appeared as `DESCRIPTIVE NISAR SINGLE OBSERVATION`, its status remained QA-held, and both hypotheses rendered `NOT EVALUATED` / `NOT TESTED`, with no evidence relationships. The source record was checksummed as `1387ef713ecb69f24dc4cc50368610022b0949ca6015a0eb398929787c1f48dd`. The draft was left in the browser session and was not saved into the local draft store.

## Boundary

This demonstrates the real measurement-to-draft software path, not a completed scientific investigation. The proposed optical observation was not searched or retrieved; no evidence was attached to either hypothesis, no explanation was evaluated, and no change or event conclusion was produced. Provider QA remains `FAIL`. The separate map capture is [`iraq-arbitrary-live-nisar-gcov-preview-2026-11-12.png`](assets/iraq-arbitrary-live-nisar-gcov-preview-2026-11-12.png).
