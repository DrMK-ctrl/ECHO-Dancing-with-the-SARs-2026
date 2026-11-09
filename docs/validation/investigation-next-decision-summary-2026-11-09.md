# Investigation next-decision summary

## Change

The investigation view now derives a compact next-decision summary from the current hypothesis and follow-up states. It surfaces unresolved interpretation gates separately from open evidence searches, while leaving completed and quality-limited screens in the audit list below.

This is workflow guidance, not a ranking model. The summary does not calculate confidence, expected information gain, source suitability, or scientific truth. It only reflects declared targets, action tracks, and availability states already recorded in the assessment.

## T163 application

Assessment: `data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-08.json`

Assessment SHA-256: `6dee4aa4c54fd4a6f683b316998885e299b75771ac83f4ed5e378334fa91c1fc`

- `F1_RTC_QA_RESOLUTION` is shown as an interpretation gate because the exact RTC-S1 products still lack a consolidated provider QA disposition. The pair remains diagnostic; this does not claim the provider will clear it.
- `F7_INDEPENDENT_SOIL_MOISTURE_SEARCH` is shown as an open evidence search for unresolved H3. Existing unsuccessful routes remain in its rationale, so the panel does not imply a suitable source has been found or authorize repeating those searches unchanged.
- Completed DSWx, GPM, SMAP, vegetation, polarization, and acquisition-condition screens remain available below as reviewed workstreams.
- The case's physical cause remains `UNRESOLVED`; no observation or scientific assessment record was changed.

## Verification

- `.venv/bin/python -m pytest -q` — **385 passed**.
- GJS executed `renderInvestigationReasoning` against the retained assessment and asserted the decision panel, F1 gate, F7 search, QA boundary, and explicit no-score limitation.
- A local ECHO server loaded the T163 case in headless Firefox through WebDriver. The browser opened `OPEN CASE INVESTIGATION`, waited for the asynchronously loaded assessment, and verified the visible assessment state, F1 and F7 entries, their no-score boundary, and that the sticky header does not cover the decision panel after scrolling.
- Browser capture: [`investigation-next-decision-browser-2026-11-09.png`](investigation-next-decision-browser-2026-11-09.png).
- `git diff --check` — passed.

The browser exercise covers this retained T163 case and the local rendering path; it does not establish generalized case-selection or scientific validation.
