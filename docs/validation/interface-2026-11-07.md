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

## Case-driven interface update

- `.venv/bin/python -m pytest -q`: **21 passed**, including review-record endpoint selection.
- Firefox/geckodriver smoke check loaded the Mozambique QA record and Nepal case-review record from separate case paths. The interface rendered the expected event label, `QA HOLD`, and the exact reviewed before-scene ID for each case.
- `git diff --check`: passed.

The interface now selects the pair pinned in `case-review.json` when available and falls back to the catalog's first metadata candidate pair for QA-review cases. The map remains an unprojected longitude/latitude view of ASF catalog footprints. These checks validate case-data presentation only; they do not validate raster access, geospatial analysis, or scientific conclusions.
