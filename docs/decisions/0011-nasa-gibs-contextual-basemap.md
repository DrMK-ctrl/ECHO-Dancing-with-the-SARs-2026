# Decision 0011: Optional NASA GIBS contextual basemap

**Date:** 2026-11-07

**Status:** Accepted

## Context

The first geographic view plots ASF catalog footprints on a longitude/latitude grid. The mission calls for an intuitive geographic investigation workspace, but ECHO does not yet load NISAR raster pixels. A geographic reference can improve orientation if it is clearly separated from SAR evidence and does not imply an analysis result.

## Decision

Offer NASA GIBS MODIS Terra Corrected Reflectance True Color through a date-specific WMS 1.1.1 request, using the current map bounds in EPSG:4326. Draw the returned image beneath ECHO's coordinate grid, catalog footprints, and search point. Use the selected catalog acquisition date for the contextual image.

Label the layer with provider, visualization, date, and “CONTEXT ONLY.” Explain that this is optical imagery, not NISAR or an analysis input, and disclose that the displayed bounds and date are requested from NASA GIBS. Let users turn the image off. On missing dates or request failure, retain the grid and catalog geometry and report the fallback in the map attribution.

Permit only `https://gibs.earthdata.nasa.gov` as an external image source in the page CSP. Do not add external scripts, styles, map SDKs, or server-side image proxying for this layer. Preserve NASA GIBS attribution in the interface and project documentation.

## Consequences

- The map gains global optical geographic context without changing catalog or SAR processing.
- A public NASA service receives the current viewport bounds and selected observation date while the basemap is on.
- GIBS visualizations are browse imagery. They do not establish SAR change, flood extent, or physical cause.
- This is not a slippy map: the current plot remains a bounded longitude/latitude view with zoom controls. Drawing AOIs, map panning, and SAR raster overlays remain future work.
- The coordinate grid remains usable offline or when NASA GIBS is unavailable.
