# NISAR GUNW product-path feasibility screen

**Screened:** 2026-11-07 UTC

**Disposition:** Scientifically relevant alternative; current sample remains on provider QA hold

**Raster pixels read:** None

## Question

Could NISAR Level 2 Geocoded Unwrapped Interferogram (GUNW) provide a useful surface-deformation path if the current GCOV candidates remain unavailable for measurement?

## Provider product and maturity evidence

ASF describes GUNW as a geocoded, 80 m posting product containing unwrapped interferometric phase, coherence, connected components, offset layers, and ionospheric phase products. The mission generates nearest-neighbor 12-day GUNW pairs in frequency A with HH or VV co-polarization. The ionospheric phase screen is present but is not applied to the GUNW data layers by default; available external phase-correction layers are also not removed. GUNW therefore offers a relevant route for investigating ground-surface displacement, but its phase values must not be presented directly as displacement without product-specific processing and an explicit reference and quality policy. [ASF GUNW product guide](https://nisar-docs.asf.alaska.edu/gunw/)

ASF documents the November 6 release of VALIDATED Level 0–2 NISAR products for acquisitions from October 21, 2026. In ECHO's bounded ASF query for GUNW VALIDATED products from October 21 through November 7, the provider returned zero records. This is the result for that query and retrieval time; it is not a claim that no later or differently indexed validated GUNW data can exist. [ASF NISAR availability and product guide](https://nisar-docs.asf.alaska.edu/products-overview/)

## Bounded PROVISIONAL sample

The reproducible screen queried PROVISIONAL GUNW at five existing ECHO candidate areas from June 17 through November 7, 2026. It retained the first response-order product per area, avoiding duplicate scene IDs. Catalog counts ranged from 14 to 25. The selected products each cover a 12-day acquisition interval:

| Area | Search results | GUNW interval | Path / frame | Provider QA |
|---|---:|---|---|---|
| Istanbul | 23 | 2026-10-09 to 2026-10-21 | 137 / 68 | FAIL |
| Rasuwa, Nepal | 24 | 2026-10-06 to 2026-10-18 | 98 / 16 | FAIL |
| Southern Mozambique | 16 | 2026-10-08 to 2026-10-20 | 114 / 165 | FAIL |
| Beirut | 14 | 2026-09-30 to 2026-10-12 | 172 / 19 | FAIL |
| Tehran | 25 | 2026-10-09 to 2026-10-21 | 136 / 71 | FAIL |

All five canonical ASF QA-summary CSVs were retrieved with Earthdata Login using the local netrc configuration. Each artifact was 2,665 bytes and contained 24 provider check rows: 23 PASS rows and one FAIL for “Passes all `identification` group checks?”. The five distinct artifact hashes, full check rows, scene identifiers, source URLs, catalog features, retrieval timestamps, and byte-range provenance are preserved in [`gunw-provisional-qa-screen-2026-11-07.json`](../../data/research/gunw-provisional-qa-screen-2026-11-07.json). The summaries do not report the QA software version or identify the failed identification subfield. No GUNW HDF5 product, QA report PDF, or phase array was read.

This sample confirms discoverable 12-day GUNW products across the five queried regions, but it does not establish usable displacement data or a workaround to the GCOV QA hold. The aggregate provider failure remains a hold; repeated summaries do not identify the cause, establish that the phase layers are unusable, or authorize ECHO to waive provider QA.

## ECHO integration assessment

ECHO currently reads and analyzes GCOV only. It has no GUNW catalog adapter, HDF5 reader, phase/geometry interpretation, coherence and connected-component mask policy, phase-to-line-of-sight displacement conversion, or GUNW-specific analysis manifest. GCOV's gamma0 power log-ratio routine is not applicable to GUNW phase values.

GUNW is worth revisiting if a candidate product clears provider QA or the relevant QA failure receives a product-specific provider disposition. A future adapter would need a separate product contract and an evaluation against product documentation and independent deformation evidence. It should preserve the interferometric temporal baseline, polarization, frequency, phase reference, quality masks, ionospheric and external corrections, and the distinction between phase and derived displacement. This screen alone does not justify implementing that adapter.

## Reproduction

With the NISAR optional dependencies installed and Earthdata Login available through the local netrc file, run:

```bash
.venv/bin/python tools/research/screen_gunw_qa.py
```

The script makes bounded metadata searches and QA-summary byte-range reads only. It records each original response and its checksum; it does not download the multi-gigabyte GUNW products.

## References

- ASF, [GUNW product definition and data layers](https://nisar-docs.asf.alaska.edu/gunw/).
- ASF, [NISAR product maturities, release dates, and product descriptions](https://nisar-docs.asf.alaska.edu/products-overview/).
- ASF, [NISAR product availability by collection and observation date](https://nisar-docs.asf.alaska.edu/availability-overview/).
- NASA/JPL, [NISAR Level 2 GUNW Product Specification](https://nisar.asf.earthdatacloud.nasa.gov/NISAR-SAMPLE-DATA/DOCS/NISAR_D-102272_RevE_NASA_SDS_Product_Specification_L2_GUNW_Nov8_2024_w-sigs.pdf).
