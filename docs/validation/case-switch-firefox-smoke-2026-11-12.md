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

## Limits

This is a browser regression smoke for case-selector transitions and map
presence. It does not establish geographic correctness, keyboard-only operation,
remote basemap availability, measurement retrieval, or scientific validity.
Those require separate checks. The smoke used the already-running local server;
it did not change application data or project source files.
