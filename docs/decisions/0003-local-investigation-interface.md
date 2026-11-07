# Decision 0003: Local, read-only investigation interface

**Date:** 2026-11-07

**Status:** Accepted for the first interface milestone

## Context

The mission calls for an interactive geographic investigation experience, while the current case contains only ASF catalog metadata. Displaying a false-color image, detected-change layer, or flood extent before acquiring and validating pixels would imply evidence that does not exist.

## Decision

Build the first interface as a dependency-light local web application served by Python's standard library. It reads one selected case catalog and its adjacent review record through read-only endpoints. Prefer `case-review.json` when present and otherwise use `qa-review.json`. Select the observation pair from the review record when specified; otherwise use the first metadata candidate pair. Plot only the selected catalog footprints and catalog query coordinate on a longitude/latitude grid. Render observation details, review status, source metadata, analysis gates, and an investigation challenge prompt alongside the map. When parsed QA report metadata records are retained beside the catalog, serve only records whose scene IDs occur in the selected case review and expose them in the QA evidence dialog. Keep PDF metadata cross-checks distinct from the separate provider CSV disposition.

Bind to `127.0.0.1` by default. Keep assets local, prohibit external scripts and network connections through the page content security policy, and do not persist analyst notes. Package the HTML, CSS, and JavaScript with the Python module.

## Consequences

- The interface can be opened without product pixels, Earthdata credentials, map tiles, or a frontend build toolchain.
- Footprint geometry represents ASF catalog coverage, not per-pixel validity or a validated common analysis area.
- Case review records govern pair selection and status presentation; they do not authorize pixel analysis or clear QA holds.
- Retained QA report metadata is inspectable from the interface, with the provider URI, checksum, software version, extracted product fields, and catalog cross-checks. The parser's limited source-rule diagnostic does not substitute for per-product provider QA checks.
- The interface cannot yet support raster comparison, classification, export, or scientific conclusions.
- The existing browser challenge prompt is a session-only reflection aid, not an audit trail or stored investigation record.
- A future raster stage must preserve the visible distinction between source observations, derived measurements, interpretations, and hypotheses.
