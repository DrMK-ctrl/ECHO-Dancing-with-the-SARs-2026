# Interface validation — 2026-11-07

## Scope

Checked the local investigation interface after adding the user-provided EESAR Systems horizontal logo and surfacing the case QA review. The interface remains a catalog and evidence-record view; this check does not validate SAR processing or scientific conclusions.

## Evidence

- `.venv/bin/python -m pytest -q`: **9 passed**.
- `git diff --check`: passed.
- Firefox headless browser smoke check: catalog details loaded, the EESAR JPEG rendered, the QA status and summary appeared, and the QA evidence dialog opened.
- At 1366 px and 500 px window widths, document `scrollWidth` matched layout `clientWidth` (1354/1354 and 488/488 px respectively; no horizontal page overflow). The browser reported a 500 px minimum when asked for 375 px.
- Rendered desktop capture: [`interface-2026-11-07.png`](interface-2026-11-07.png).

## Limits

This is a local browser smoke check, not a complete accessibility, keyboard, or cross-browser review. The page contains catalog footprints and metadata, not SAR pixels. Product QA remains `QA_HOLD`; no change metric or event interpretation was produced.
