# Decision 0016: add bounded Bhoonidhi S-SAR catalog discovery

**Status:** Implemented for authenticated metadata discovery; live account-backed query and product validation remain open

## Context

ASF-distributed NISAR L-SAR GCOV candidates have provider identification-group failures. ISRO publishes daily NISAR S-SAR products, including GCOV, through Bhoonidhi. Its API exposes a STAC search and requires a registered account and bearer token. S-SAR has a separate provider, instrument-specific product paths, QA artifacts, and known release limitations; it cannot be passed through the ASF path by assuming the products are interchangeable.

## Decision

Add a separate, read-only catalog client for the exact `NISAR_SSAR_GCOV` Bhoonidhi collection. The client:

- prompts locally for credentials through the CLI, without echoing the password;
- keeps the short-lived token in memory and never serializes it;
- searches one WGS84 rectangle and acquisition-time interval at a time;
- filters to products whose provider `Online` property is `Y`;
- requests up to the provider limit of 500 results per page and follows STAC `next` links sequentially, with a default 10-page cap, a hard 20-page cap, and a 20 MiB cumulative response limit;
- validates continuation links against the HTTPS Bhoonidhi `/data/search` endpoint before forwarding the in-memory bearer token, rejects redirects, and marks a result incomplete if a next page remains at the cap;
- preserves the returned STAC features and records query parameters, provider, instrument, retrieval time, per-page checksums, byte counts, and pagination-completeness state.

Catalog results are discovery evidence only. This client does not download products, interpret QA, normalize S-SAR items as ASF records, pair scenes, or authorize measurements. Product access and scientific compatibility require separate provider-specific checks.

## Verification and limits

- Unit tests exercise local credential handling, bearer-header placement, GET and POST STAC pagination, next-link headers and body merging, same-origin restrictions, repeated-request rejection, bounds and date validation, response-size/schema gates, provenance capture, and exclusion of tokens from outputs.
- The provider's official API specification documents authenticated STAC search, `NISAR_SSAR_GCOV`, online filtering, pagination links, and the 500-item maximum.
- No registered Bhoonidhi account was available for a live authenticated query at implementation time. The actual S-SAR item schema, product assets, online statuses, and QA reports have not been verified from live responses.
- ISRO reports baseline P00500, potential future calibration revision, and residual radiometric banding/RFI in some low-SNR conditions. Those caveats remain relevant to any later case selection.

## References

- ISRO/Bhoonidhi, [API specification](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/).
- ISRO/Bhoonidhi, [NISAR S-SAR release](https://bhoonidhi.nrsc.gov.in/NISAR/NisarProducts.html).
- NASA/ASF, [NISAR Vertex access guide](https://nisar-docs-test.asf.alaska.edu/vertex).
