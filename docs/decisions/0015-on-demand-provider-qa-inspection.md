# Decision 0015: inspect provider QA summaries on demand

**Date:** 2026-11-07

**Status:** Implemented for selected ASF NISAR GCOV catalog records

## Context

Catalog discovery can return many products not present in a retained case review. Those records have no local provider QA disposition, so users could not inspect the provider's per-product CSV checks from the interface.

## Decision

Add a local `POST /api/qa-summary` endpoint and a selected-observation **FETCH QA** action. The request accepts only the scene ID, ASF product URI, processing level, and collection name from a catalog feature. The server revalidates the product against the supported NISAR GCOV collections and exact ASF HTTPS URL shape before calling the existing authenticated reader. Request bodies are limited to 4 KiB; the reader limits remote QA-summary content to 64 KiB.

The interface shows every parsed provider check row, the provider's aggregate disposition, original summary URI, retrieval timestamp and method, received size, requested range bytes, and SHA-256. Results are held in browser memory for the session. The user can export a JSON attachment containing the complete catalog feature and query alongside the provider QA record. The export endpoint checks that the catalog product and QA artifact refer to the same supported ASF scene and does not retain a server-side copy. The existing retained QA-report metadata remains a separate evidence record.

The endpoint does not read HDF5 identification metadata or radar arrays. It does not reinterpret provider results, clear a QA hold, establish product suitability, or authorize measurement. Provider retrieval or parsing errors remain visible as errors and do not become a passing disposition.

## Validation

See [`on-demand-provider-qa-2026-11-07.md`](../validation/on-demand-provider-qa-2026-11-07.md) for endpoint tests and live Firefox/Earthdata retrieval and JSON-export evidence.
