# Decision 0010: on-demand, read-only ASF catalog discovery

**Status:** Implemented; endpoint and live ASF searches exercised

## Context

The first local interface displayed a saved ASF catalog snapshot. Users could inspect its footprints and source records, but could not explore a different point or time interval without running a command and selecting a new case file. The catalog client already supported public metadata searches for NISAR GCOV products at BETA, PROVISIONAL, and VALIDATED maturity.

## Decision

Add a local interface search for longitude, latitude, start and end dates, and GCOV maturity. The browser submits a bounded JSON request to `POST /api/catalog`; the Python server validates the exact request fields and delegates to the existing ASF catalog client. Limit each query to 250 features. Return the existing provenance-aware catalog record, including pair candidates and catalog-only/pixel-not-downloaded status.

Keep results in browser memory for the current page session. Do not alter case records, download product pixels, use Earthdata credentials, or imply QA review or scientific analysis. Show compatible metadata pairs as candidates only; show individual records when no pair passes screening and an explicit empty state when no observations match.

## Evidence and limits

- Input coordinates must be finite and within geographic bounds; dates must be exact ISO calendar dates in chronological order; maturity must be one of the supported GCOV values.
- The request body is capped at 8 KiB, the server fixes `max_results` at 250, and upstream error details are not returned to the browser.
- Automated tests cover valid metadata-only responses, invalid input rejection before the catalog call, and safe upstream failure handling.
- A live endpoint query for the Nepal search point returned six ASF features and two metadata pair candidates; the response reported `pixels_downloaded: false`.
- A live query with no matching observations rendered an explicit zero-observation state without map footprints.
- Search-result product QA is not fetched automatically. Pixel access, QA retrieval, raster display, geospatial selection, case persistence, and analysis remain separate capabilities.
- The map is a longitude/latitude plot of ASF catalog footprints, not a basemap, raster view, or validated common-pixel area.

## Consequences

The investigation workspace now supports geographic and temporal catalog exploration without a frontend build system or multi-gigabyte downloads. Every search is reproducible from its visible query fields and returned catalog record, while unreviewed products remain clearly unreviewed. A later decision is needed before saving searches into durable case records or integrating product QA and pixel access into the interface.
