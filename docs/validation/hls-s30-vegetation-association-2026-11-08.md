# HLS S30 vegetation screen and association — 2026-11-08

## Result

NASA LP DAAC CMR identified same-tile HLS Sentinel-2 S30 v2.0 observations around both T163 RTC-S1 dates. Bounded red (B04), NIR (B8A), and Fmask COG windows were read for the exact WGS84 AOI and retained as checksummed subsets. The pixel-center AOI and valid-data comparison produced 25 common clear-land pixels from 1,152 AOI centers (2.1701%). The earlier scene has 29 eligible pixels and the later scene 997; the low common count is driven by the earlier scene's Fmask aerosol/quality exclusions.

The median NDVI change on those 25 pixels is +0.000474 (10th–90th percentile: −0.0610 to +0.0318). This is a descriptive statistic on sparse, spatially dependent support; no inferential test was calculated. The checksum-linked native-grid overlay retains 11 SAR cells at 75% optical-area coverage (25 cells at 50%, 39 at 25%), with descriptive Pearson r = −0.411 for the 75% set. The threshold sensitivity and small spatial sample make this coefficient nondiscriminating.

## Acquisition and source trace

- Provider/product: NASA LP DAAC, Harmonized Landsat and Sentinel-2 S30 v2.0, collection `C2021957295-LPCLOUD`.
- Before: `HLS.S30.T22JDM.2024129T132241.v2.0`, Sentinel-2A MSI, 2024-05-08 13:30:53.463 UTC.
- After: `HLS.S30.T22JDM.2024154T132239.v2.0`, Sentinel-2B MSI, 2024-06-02 13:30:52.554 UTC.
- Compared SAR acquisitions: 2024-05-08 22:07:19 UTC and 2024-06-01 22:07:19 UTC; optical-minus-SAR offsets −8.607 and +15.393 hours.
- Bands and screen: B04, B8A, and Fmask; cloud, cloud-adjacent, shadow, snow/ice, water, high-aerosol, invalid-reflectance, and nonpositive-denominator pixels are excluded from NDVI support.
- Derived association inputs: SAR record SHA-256 `57fc5735c4e347394816d5d64b6406451ba67b727009b4b94efbd62152dde8ef`; S30 screen SHA-256 `255c5c19c1b8f13a81c4cbf73251b347943094c39a7a1e273888c35d5aa673e9`.
- HLS product documentation: [S30 v2.0](https://lpdaac.usgs.gov/products/hlss30v020/), [L30 v2.0](https://lpdaac.usgs.gov/products/hlsl30v020/), [HLS User Guide](https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf).

## Investigation disposition

The result is classified `DOES_NOT_DISTINGUISH` for H4 (vegetation-state change), following the mechanism split in Decision 0042. H4 remains `UNRESOLVED`; the optical pair does not validate SAR, establish vegetation causality, measure soil moisture, or resolve the event cause. The screen and association are source-inspectable through the T163 assessment. A targeted follow-up remains open for a better-supported independent source.

## Verification performed

- Bounded authenticated COG reads completed for both selected S30 granules; selected source subsets and checksums were retained.
- The reusable HLS reader/evaluator was exercised with S30 B8A as well as its existing L30 B05 path.
- T163 assessment rebuilt from retained source records; API checks enforce artifact hashes, product identity, lineage, and source links.
- `.venv/bin/python -m pytest -q` — 278 passed.
- Python bytecode compilation and `git diff --check` — passed.
- Headless Firefox opened the linked assessment, rendered the S30 card and acquisition-timeline row, and opened the source-inspection dialog for the S30 screen record.
- Node.js is not installed; browser execution provided the JavaScript integration check.

## Limitations

This screen does not constitute a product provider QA clearance for the Sentinel-1 pair. Its optical clear-pixel count is insufficient for a mechanism test, spatial pixels are not independent replicates, and the reported correlation is descriptive only. No change in causal disposition or event interpretation is justified.
