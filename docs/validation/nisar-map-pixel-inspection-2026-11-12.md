# NISAR map pixel inspection — 2026-11-12

## Result

Firefox opened ECHO's retained, checksummed NISAR GCOV diagnostic preview and selected a cell at the center of the mapped AOI. The source inspector exposed the pixel's quantitative backscatter and quality values. This browser pass used the retained local record and made no provider request.

## Pixel-level cross-check

The interface selected source-grid row `8070`, column `8481`. The retained window begins at row `8015`, column `8436`, so this maps to array index `[55][45]`. Independently reading the checksummed record `data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json` at that array index gives:

- γ⁰: `0.07644271850585938` linear, or `−11.16663876678507 dB` using `10 log10(γ⁰)`.
- GCOV mask: `1`; number of looks: `9.457941055297852`; input-data exception mask: `0`.
- Exact AOI pixel-center selection: `true`.

The browser displayed the rounded equivalents (`0.0764427`, `−11.17 dB`, mask `1`, 9.4579 looks, exception `0`). The underlying provider QA is still `FAIL`; a valid display pixel does not clear product QA or authorize temporal analysis. The complete window and array checksums remain in the retained source record.

Screenshot: [`iraq-nisar-map-pixel-inspector-2026-11-12.png`](assets/iraq-nisar-map-pixel-inspector-2026-11-12.png), SHA-256 `ecd1fa7d67c5006ea15544a32c5b607819898b08e55e94fad76a88b1f28e9c8e`.

## Limits

This verifies click-to-pixel inspection, numerical agreement with the retained source array, AOI membership, and display of mask/looks/exception metadata for this one retained case. It does not repeat the authenticated provider retrieval, validate other map grids, clear QA, or establish any temporal change or physical interpretation.
