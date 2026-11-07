# Decision 0003: Local, read-only investigation interface

**Date:** 2026-11-07

**Status:** Accepted for the first interface milestone

## Context

The mission calls for an interactive geographic investigation experience, while the current case contains only ASF catalog metadata. Displaying a false-color image, detected-change layer, or flood extent before acquiring and validating pixels would imply evidence that does not exist.

## Decision

Build the first interface as a dependency-light local web application served by Python's standard library. It reads one catalog JSON record and exposes it through a read-only endpoint. The map plots catalog footprints and the query coordinate on a longitude/latitude grid. Observation details, source metadata, analysis gates, and an investigation challenge prompt sit alongside the map.

Bind to `127.0.0.1` by default. Keep assets local, prohibit external scripts and network connections through the page content security policy, and do not persist analyst notes. Package the HTML, CSS, and JavaScript with the Python module.

## Consequences

- The interface can be opened without product pixels, Earthdata credentials, map tiles, or a frontend build toolchain.
- Footprint geometry represents ASF catalog coverage, not per-pixel validity or a validated common analysis area.
- The interface cannot yet support raster comparison, classification, export, or scientific conclusions.
- The existing browser challenge prompt is a session-only reflection aid, not an audit trail or stored investigation record.
- A future raster stage must preserve the visible distinction between source observations, derived measurements, interpretations, and hypotheses.
