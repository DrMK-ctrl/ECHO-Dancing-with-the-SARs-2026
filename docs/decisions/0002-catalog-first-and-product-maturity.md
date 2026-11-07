# Decision 0002: begin with catalog evidence and preserve product maturity

- **Date:** 2026-11-07
- **Status:** Accepted for the first implementation milestone

## Context

NASA has published an official NISAR GCOV before/after visualization of the January 2026 Mozambique floods. The ASF catalog contains two GCOV scenes that intersect the Chókwè-area search point on January 5 and January 17. Both are in the same BETA collection, path, frame, direction, polarization, production configuration, range bandwidth, and composite release identifier. Each HDF5 product is about 4 GB and requires Earthdata authentication to retrieve.

## Decision

Implement catalog discovery and metadata-level pairing first. Carry the collection/maturity and processing identifiers into every candidate. Only pair products with matching acquisition and processing metadata and intersecting catalog footprints. Label these as metadata candidates until QA, actual valid-pixel overlap, and raster grid alignment have been checked.

Use the January Mozambique pair as an exploratory real-NISAR pilot if pixel access and QA permit. Preserve its BETA maturity in all outputs. Do not combine it in a quantitative pair with PROVISIONAL products. The BETA case does not by itself establish a calibrated estimate of flood extent or provide independent validation of the published NASA interpretation.

## Consequences

- Initial implementation can be exercised using the public ASF catalog without Earthdata credentials.
- Pixel analysis requires a local Earthdata Login configuration, and will use spatially limited reads where the data format permits.
- Tests may use clearly identified synthetic metadata fixtures; they do not count as NISAR validation.
- A separate, higher-maturity case may be selected later if it has both a scientifically relevant event and suitable independent evidence.
