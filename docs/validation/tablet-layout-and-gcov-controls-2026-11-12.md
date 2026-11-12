# Tablet layout and GCOV preview controls — 2026-11-12

## Result

Firefox runtime review found and fixed two user-facing defects in the supported map workflow. At widths from 761 through 999 CSS pixels, the page no longer enforces a 1,000-pixel minimum: the map and evidence panel remain side by side without horizontal document overflow. A malformed `B` option in the GCOV frequency selector had also swallowed the following layer selector during browser parsing, causing `renderObservationDetails` to fail when a scene was selected. The option markup is corrected, and the serving test now parses and asserts both frequency options plus the layer selector.

## Runtime evidence

The loopback application ran in `--read-only-demo` mode with the retained Iraq NISAR case. Firefox loaded the checksummed HHHH preview record already included in the case; no product measurement was fetched. The record remains `QA_HELD_DIAGNOSTIC_PREVIEW` with provider QA `FAIL`.

| CSS viewport | Document client / scroll width | Map bounds | Evidence panel bounds | Browser state |
|---:|---:|---:|---:|---|
| 768 px | 756 / 756 px | 16–464 px | 476–756 px | No toast; selected scene; frequency A/B and HHHH/HVHV layer options present |
| 900 px | 888 / 888 px | 16–596 px | 608–888 px | No toast; GCOV layer selector present |

The 768-pixel capture is [`iraq-curated-preview-tablet-768-2026-11-12.png`](assets/iraq-curated-preview-tablet-768-2026-11-12.png), SHA-256 `bb1b0173830aff17eb5c533c5a3a588e15a73753aef0a71db33b88cc77a17ddc`.

## Verification and limits

- `.venv/bin/python -m pytest -q tests/test_web.py::test_local_interface_serves_static_app_and_read_only_catalog tests/test_investigation.py::test_tablet_layout_keeps_map_and_evidence_panel_within_viewport` — focused serving and breakpoint regression checks.
- Firefox verified the parsed controls, absence of the runtime error toast, selected real preview rendering, and viewport bounds at 768 and 900 CSS pixels.

This covers two tablet widths and the retained read-only Iraq case; it does not establish every screen size, keyboard accessibility, provider QA clearance, temporal comparability, or a physical-change result. The NISAR preview remains QA-held diagnostic evidence.
