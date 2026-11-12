# Registered case-switch browser smoke — 2026-11-12

## Scope

A fresh headless Firefox session opened the existing loopback application at
`http://127.0.0.1:8766/`. The actual page loaded to `document.readyState=complete`
and populated all six registered cases in the selector.

## Interaction

The browser selected each registered case in turn through the visible case
selector and dispatched the normal `change` event. After each transition, the
selected case ID matched the requested ID, the interactive SVG map remained
present with `viewBox="0 0 1000 600"`, and the visible map dimensions were
788 × 286 CSS pixels. No visible `role=alert` error appeared during switching.

All six case IDs were exercised:

- `rio-grande-do-sul-t163-349925-diagnostic-2024`
- `iraq-2026-nisar-gcov-diagnostic`
- `istanbul-2026-flood`
- `mozambique-2026`
- `nepal-2026-rasuwa`
- `rio-grande-do-sul-cross-sensor-diagnostic-2024`

The geographic center readout also changed to the registered case's search/AOI
center in each case: T163 and its cross-sensor assessment `51.2350° W,
30.0350° S`; Iraq `41.2100° E, 36.7100° N`; Istanbul `28.9900° E,
41.1050° N`; Mozambique `33.5000° E, 24.5000° S`; and Nepal `85.5500° E,
28.3000° N`. Firefox reached `document.readyState=complete`; the map SVG was
present for all six cases, and no alert was shown. Cases without a loaded radar
measurement retained the explicit “NO RADAR PIXELS LOADED” warning.

## World-view area selection

The browser selected **World View**, enabled **Select Area**, and dragged a
rectangle across the map with pointer input. ECHO rendered the selection and
reported a WGS84 center of `0.2774° W, 1.9784° S`. The catalog-search dialog
retained the rectangle as west/south/east/north bounds of approximately
`[-31.0628, -23.0567, 30.5081, 19.0999]`. This deliberately broad rectangle
shows that the global view supports direct geographic selection; users should
zoom in when they need a smaller AOI. The browser interaction did not submit a
catalog query or retrieve satellite pixels.

## Limits

This is a browser regression smoke for case-selector transitions and map
presence. It does not establish geographic correctness, keyboard-only operation,
remote basemap availability, measurement retrieval, or scientific validity.
Those require separate checks. The smoke used the already-running local server;
it did not change application data or project source files.
