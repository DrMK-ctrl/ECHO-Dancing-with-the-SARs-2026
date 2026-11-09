# Decision 0093: retain a bounded HLS candidate screen in the investigation

**Date:** 2026-11-09
**Status:** Implemented

## Context

T024's vegetation follow-up remained open because the May 8/June 1 HLS L30 pair had only 265 common clear-land centers (23% of the AOI), while the selected HLS S30 pair had no common clear-land support. Repeating either acquisition would not improve the evidence. A wider, bounded CMR query found a distinct June 9 L30 scene that could be screened once for a material coverage improvement.

## Decision

Retain the exact CMR responses, candidate identities, query windows, selected product assets, and Fmask counts. Treat a candidate that fails paired clear-land support as an explicit quality-limited search result. Do not calculate NDVI change, associate it with SAR, or treat it directionally in H4. Keep the follow-up open because these date windows are not an exhaustive search.

Schema 4 links the screen to the exact assessment case and SAR pair. Both the builder and web validator recheck CMR response hashes and candidate lists, bounded-asset hashes, AOI support, and Fmask counts. The UI presents the result beside the existing optical context and opens its full source record.

## Validation

See [T024 extended HLS candidate screen](../validation/t024-hls-extended-candidate-screen-2026-11-09.md).
