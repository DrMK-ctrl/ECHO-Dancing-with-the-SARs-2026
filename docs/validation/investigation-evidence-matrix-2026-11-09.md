# Investigation evidence matrix — 2026-11-09

## Result

The T163 investigation assessment now has an optional evidence/hypothesis matrix above its detailed hypothesis cards. It renders the retained source-to-hypothesis relationship records and leaves every missing relationship visibly unassessed.

The active T163 assessment contains 24 evidence artifacts and 6 hypotheses (144 possible source-hypothesis combinations). It has 18 analyst-entered relationships: one `SUPPORTS`, twelve `DOES_NOT_DISTINGUISH`, and five `LIMITS_INTERPRETATION`. The other 126 combinations have no recorded relationship, and no `CONTRADICTS` relationship is recorded. The matrix displays these states without adding or revising any relationship or hypothesis disposition.

## Browser verification

- Headless Firefox opened the active T163 assessment and expanded the matrix.
- It rendered 24 source rows and 6 hypothesis columns, with 126 explicitly unassessed cells and direct source-inspection buttons.
- At a 1366 px viewport, the matrix scroll container fit within the dialog and the document had no horizontal overflow (`1354/1354` CSS pixels).
- The visual record is [`investigation-evidence-matrix-2026-11-09.png`](investigation-evidence-matrix-2026-11-09.png).

## Automated verification

- `tests/test_investigation_renderer.py` exercises the renderer with a controlled fixture. It checks a contradiction label, an unassessed cell, and HTML escaping.
- The fixture verifies presentation logic only; it is not satellite evidence or a scientific accuracy evaluation.
