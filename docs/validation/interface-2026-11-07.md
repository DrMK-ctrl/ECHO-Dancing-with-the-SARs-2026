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

## On-demand catalog search

- The local `POST /api/catalog` endpoint was exercised against ASF for a Nepal point/date/maturity query. It returned six metadata features and two metadata-compatible pair candidates; the response marked pixels as not downloaded.
- A live no-result search produced the explicit no-observations state and zero map footprints.
- Firefox headless smoke checks confirmed the search dialog, successful pair-candidate rendering, and zero-result rendering. A desktop screenshot was inspected for control clipping and dialog layout.
- Automated endpoint tests cover valid requests, invalid-input rejection before ASF access, and safe handling of catalog failures. Full automated validation is recorded with the implementation commit.

Catalog search remains metadata-only. This browser evidence does not validate product QA, raster display, pixel registration, change analysis, responsive accessibility, or scientific conclusions.

## Istanbul candidate case

- Started the local interface with `data/cases/istanbul-2026/catalog.json` and verified the served catalog/review records over HTTP.
- Firefox headless loaded the Istanbul candidate, pinned the October 9/21 NISAR pair, and rendered `QA HOLD`, the provider `FAIL`, both acquisition dates, and the scene identifier.
- Opened the QA evidence dialog and confirmed it exposes the product QA summary/report source URLs and QA software version.
- Screenshot: [`istanbul-interface-2026-11-07.png`](istanbul-interface-2026-11-07.png).

This validates case-record presentation and source inspection only. It does not validate NISAR pixels, flood extent, registration, or a scientific conclusion.

## Case-linked QA report inspector

- `/api/qa-reports` returned the two retained Istanbul QA report records and filtered a deliberately stale scene ID in the endpoint test.
- Firefox/geckodriver loaded the case, selected the after acquisition, and rendered two readable report cards with provider links, checksums, report/product versions, catalog cross-checks, and an explicit note that the source-code diagnostic does not attribute the provider failure.
- The complete machine-readable review and report records remain available in the collapsed details section.
- `.venv/bin/python -m pytest -q`: **80 passed**; `compileall` and `git diff --check` passed.
- Screenshot: [`istanbul-qa-report-evidence-2026-11-07.png`](istanbul-qa-report-evidence-2026-11-07.png).

The evidence dialog displays retained report metadata. It does not retrieve reports on page load, change the provider CSV disposition, clear the QA hold, or establish raster suitability.
