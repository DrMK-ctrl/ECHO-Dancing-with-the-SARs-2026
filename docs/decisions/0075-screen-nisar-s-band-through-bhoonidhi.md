# Decision 0075: Screen NISAR S-band data through Bhoonidhi

**Date:** 2026-11-08
**Status:** Research gate; no S-band data retrieved or integrated

## Context

The current ASF NISAR L-band GCOV pair candidates are held by provider QA failures in the identification group. ECHO must keep those dispositions and continue to search for a scientifically suitable NISAR route without assuming that the same release issue applies to products distributed by ISRO.

ISRO reports that daily processed NISAR S-band products from Cycle 25 onward (beginning 2026-07-08) are available through Bhoonidhi, with current products at baseline v1.4.0 / CRID P00500. The released suite includes GCOV and interferometric products. ISRO's NISAR page shows a sample image labeled Amazon River, Brazil. This establishes a potentially relevant South American S-band data route; it does not establish catalog coverage, repeat observations, product quality, or an event pair for ECHO's current AOI.

## Decision

Before implementing an S-band adapter, perform a bounded catalog screen through the official Bhoonidhi route for the current Rio Grande do Sul AOI and for a small set of scientifically justified alternate cases if needed. Retain complete search parameters and page counts. For any candidate, confirm acquisition compatibility, product baseline, polarization and measurement semantics, online status, and product-specific quality information before retrieving a bounded window.

Treat S-band and L-band as distinct NISAR instruments and product sources. Do not assume that an L-band reader, QA interpretation, physical sensitivity, or calibration status transfers to S-band. Keep any S-band evidence distinct from ASF L-band, Sentinel-1-derived OPERA, and other context sources.

The Bhoonidhi API specification requires registered-user authentication and says API access may require contacting NRSC. Credentials and tokens must remain local; no account secrets belong in the repository or chat. The user has offered to create an account but has not yet reported that it is active.

On 2026-11-08 at 16:54 UTC, an unauthenticated GET to the documented `https://bhoonidhi-api.nrsc.gov.in/data/collections` endpoint returned HTTP `401` with `UNAUTHORIZED` / `Invalid session detected! Please login again.` No credentials were sent. This confirms that live collection screening cannot proceed anonymously; it does not indicate that NISAR S-band products are absent.

## Acceptance gates

- The exact requested AOI and date range are represented by complete, bounded catalog results; an example image or observation-plan map is not treated as an available product.
- At least two exact product IDs form a compatible temporal pair before temporal processing is considered.
- Each product's provider QA and available product-specific quality artifacts are retained and evaluated without a locally inferred pass overriding an upstream failure.
- Any future reader is based on the official S-band product specification and is separately tested against retained S-band data.
- If no appropriate S-band pair exists, record the screened coverage and move to another scientifically defensible case or data route without claiming an S-band result.

## Sources

- [ISRO NISAR S-band product release](https://www.isro.gov.in/NISARS_Band_SAR_Data_Products_Release.html) — released products, processing baseline, coverage scope, calibration notes, and known residual artifacts.
- [Bhoonidhi NISAR information page](https://bhoonidhi.nrsc.gov.in/NISAR/) — instrument, product-family, and data-access overview; includes an illustrative Amazon River, Brazil image.
- [Bhoonidhi API specification](https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/) — registration, authentication, STAC search, and download requirements.
- [NASA NISAR mission overview](https://science.nasa.gov/mission/nisar/mission-overview/) — distinguishes ASF L-band access from Bhoonidhi S-band and selected L-band access.
