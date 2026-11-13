# Curated read-only controls — Firefox validation, 2026-11-13

## Finding

The Iraq curated demo correctly rejected catalog searches and measurement or draft mutations at the server, but the browser still presented some of those actions as available. In particular, the map renderer's generic control-state update re-enabled the retained-measurement button after its read-only state was set. Clicking the catalog action opened a dialog whose request could only end in the server's read-only rejection.

## Change

The UI now disables provider catalog actions, new GCOV retrieval, pair analysis, and investigation-draft creation in curated read-only mode. Retained measurements, source inspection, the adversarial review, local map navigation, and optional NASA GIBS imagery remain available. The server-side read-only checks remain authoritative. Interactive mode continues to leave provider catalog controls available.

The mode banner now describes the actions available to the user rather than referring to HTTP methods or internal server rejection behavior.

## Verification

- Firefox 158.0.1 with geckodriver, local Iraq read-only application at `127.0.0.1:8767`:
  - `FIND OBSERVATIONS`, `OPERA RTC-S1`, `NISAR S-SAR`, `LOAD BACKSCATTER`, `ANALYZE PAIR`, and `START INVESTIGATION` were disabled.
  - Clicking the disabled catalog action did not open its dialog or issue a request.
  - The retained NISAR measurement continued to show provider QA `FAIL`; **Challenge This Observation** still opened its review.
- Selecting the other Iraq acquisition hid the retained raster; returning to the source acquisition restored the same measurement. The local preview control could hide and restore the checksummed record without a provider request. Selecting a different WGS84 area kept the cached pixels hidden even after returning to their source acquisition; the area-specific preview control stayed disabled.
- Firefox against the interactive T163 workbench at `127.0.0.1:8766`: ASF, OPERA, and Bhoonidhi catalog controls remained enabled; the read-only banner remained hidden.
- `.venv/bin/python -m pytest -q`: **498 passed**.

This validates these controls in the local retained cases and does not establish availability of external catalog services or change the scientific status of any observation. The Iraq NISAR preview remains QA-held and diagnostic.
