# Decision 0076: Follow bounded Bhoonidhi STAC pagination

**Date:** 2026-11-08
**Status:** Implemented and software-tested; live authenticated pagination remains unverified

## Context

The Bhoonidhi S-SAR GCOV client requested one result page and recorded whether a `next` link existed. A spatial and temporal query that crossed the provider's page boundary could therefore omit catalog records unless the user noticed the flag and manually repeated the search. This could hide a compatible acquisition and make a catalog result look complete when it was not.

## Decision

Follow the provider's STAC `next` link sequentially, supporting the link's GET or POST method, body merge behavior, and continuation headers. Keep requests bounded to at most 20 pages (default 10) and 20 MiB of total response bytes. If another page remains when the configured page cap is reached, return the retrieved items with `pagination_complete=false` and `has_next_page=true`.

Before each request, resolve the continuation URL and require HTTPS, the exact Bhoonidhi API host, and the `/data/search` path. Do not follow redirects or permit a continuation link to replace the Authorization header or override transport headers. Detect repeated request signatures to prevent pagination loops. Keep the bearer token only in request headers and out of retained output. Record each page's response SHA-256, byte count, and item count alongside the full original search query.

The combined FeatureCollection is a client-side aggregation of the returned pages. It is catalog metadata only and does not establish product availability beyond the provider's `Online=Y` field, product QA, acquisition compatibility, or scientific suitability.

## Verification

- Focused tests cover GET pagination, POST continuation-body merge, continuation headers, complete and capped results, cross-origin rejection, repeated-request rejection, and the existing authentication and query validation behavior.
- Full-suite and compile results are in [the pagination validation record](../validation/bhoonidhi-pagination-2026-11-08.md).
- The actual Bhoonidhi account-backed response schema and pagination behavior still require a live registered-account query.

## References

- ISRO/Bhoonidhi, [API specification](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/), which documents `rel=next` links and a maximum page limit of 500 items.
- Radiant Earth, [STAC API Item Search paging examples](https://github.com/radiantearth/stac-api-spec/blob/release/v1.0.0/item-search/examples.md), which define GET and POST continuation links, including request bodies and headers.
