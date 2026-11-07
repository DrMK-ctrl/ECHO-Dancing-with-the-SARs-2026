# Decision 0017: Interactive, bounded GCOV single-scene preview

**Status:** Accepted for the first real-measurement interface milestone
**Date:** 2026-11-07

## Context

No NISAR GCOV temporal pair has cleared the existing provider-QA and measurement gates. That does not prevent verifying one real observation through authenticated access, geographic selection, map placement, and source inspection. The existing bounded HDF5 reader already reads geographic windows and their product quality layers.

## Decision

- Keep catalog search, product retrieval, and scientific analysis as separate steps. A catalog match or preview does not imply suitability for comparison.
- For each GCOV scene, expose only real-valued diagonal layers inferred from the scene's catalog polarization metadata. Let the user choose frequency A or B; a missing requested HDF5 layer must return a clear error rather than substitute another layer.
- Request the provider QA summary before reading the raster window. Preserve its status and artifact hash. QA `FAIL` permits an explicitly QA-held diagnostic preview, but never authorizes temporal analysis or physical interpretation.
- Draw each selected pixel cell from its source grid corner coordinates transformed to WGS84. Retain linear gamma-zero values in the evidence record; label the `10 log10` display transform and its AOI percentile stretch.
- Bound previews to 65,536 pixels and retain the selected AOI mask, product mask, exception mask, number-of-looks values, coordinates, source identifiers, retrieval details, and array checksums in the downloadable record.
- Consume ASF CMR search results page by page up to a 1,000-record interface cap. Mark cap-sized results as potentially incomplete and give the analyst a date/area refinement action. Do not silently treat the cap as complete coverage.

## Consequences and limits

This advances real NISAR measurement display independently of a QA-cleared temporal pair. The preview currently uses ASF-distributed NISAR L-band GCOV; it does not make S-band data compatible or promote QA-held products. Catalog polarization metadata suggests available diagonal layers but does not prove a specific HDF5 frequency/layer exists; the bounded reader remains authoritative and fails clearly when it does not. The map's color stretch is for visualization, not a physical threshold. Large AOIs must be reduced or zoomed before retrieval. Pair analysis remains gated on provider QA, compatible products, aligned grids, and common valid pixels.

The ASF pagination mechanism is `asf_search.search_generator()`, whose CMR pages contain 250 products. [ASF best practices](https://docs.asf.alaska.edu/asf_search/BestPractices/) recommend page-wise iteration for large result sets.
