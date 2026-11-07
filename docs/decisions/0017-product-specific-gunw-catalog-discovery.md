# Decision 0017: add product-specific GUNW catalog discovery

**Status:** Implemented as a metadata-only server route; browser integration and pixel visualization remain open

## Context

ECHO has a bounded GUNW HDF5 reader and research records for real GUNW products, but its live catalog client and interface search only GCOV. GUNW carries different measurements and supports different operations, so it should not be represented as a GCOV result or sent through GCOV pairing and analysis logic.

## Decision

Add a separate ASF GUNW search function and `/api/gunw-catalog` route. It:

- accepts point or WGS84 rectangle searches and PROVISIONAL or VALIDATED maturity;
- caps result requests and returned records at 100;
- validates each returned feature against supported GUNW identifiers, collections, and canonical ASF URLs;
- returns a reduced metadata feature set with an explicit metadata-only interpretation limit.

The route does not download products, retrieve QA, pair observations, render pixels, or authorize analysis. The current browser workflow remains GCOV-only until a GUNW inspection flow can preserve provider QA and the GUNW-specific scientific limits end to end.

## Verification and limits

- Unit tests verify ASF query parameters, the server result cap, feature allowlisting, and rejection of unsupported maturity.
- A live bounded PROVISIONAL search around Istanbul returned five GUNW metadata records from ASF, including the known October 9–21 product.
- No GUNW raster was read by this catalog route, and its results do not establish product quality or scientific suitability.
