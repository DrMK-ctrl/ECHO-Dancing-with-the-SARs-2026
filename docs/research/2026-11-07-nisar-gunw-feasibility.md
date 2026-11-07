# NISAR GUNW product-path feasibility screen

**Screened:** 2026-11-07 UTC

**Disposition:** Scientifically relevant alternative; one product's metadata and QA report reviewed, provider QA failure retained

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

All five canonical ASF QA-summary CSVs were retrieved with Earthdata Login using the local netrc configuration. Each artifact was 2,665 bytes and contained 24 provider check rows: 23 PASS rows and one FAIL for “Passes all `identification` group checks?”. The five distinct artifact hashes, full check rows, scene identifiers, source URLs, catalog features, retrieval timestamps, and byte-range provenance are preserved in [`gunw-provisional-qa-screen-2026-11-07.json`](../../data/research/gunw-provisional-qa-screen-2026-11-07.json). The summaries do not report the QA software version or identify the failed identification subfield.

### Product-specific follow-up: Istanbul

NASA's NISAR subject-matter expert replied on October 22, 2026 to a question describing PROVISIONAL GUNW products with an identification-group QA failure and other checks passing. The expert said users may ignore the QA summary “at this stage.” The same reply says consistent CRIDs are suitable for time-series use, mixing P05023 with earlier CRIDs should be done with caution, nominal interferograms are nearest-neighbor acquisitions about 12 days apart, and phase-correction layers are expected to be subtracted from unwrapped phase. It also explains that N/F reflects orbit/attitude accuracy; for nominal products F is usually from attitude, with special care potentially needed for urgent-response products. These are general product-team guidance, not a revised per-scene QA disposition, an explanation of the failed field, or proof that a particular phase measurement is scientifically suitable. ECHO preserves the ASF CSV's `FAIL` alongside the expert guidance rather than replacing either record; the expert reply supports further user evaluation of these products. No correction is applied by ECHO. [NASA Earthdata Forum discussion](https://forum.earthdata.nasa.gov/viewtopic.php?t=8325)

For the Istanbul sample, ECHO retrieved the canonical ASF QA report PDF (1,035,490 bytes; SHA-256 `66578e1e0f86515c2fe4428cd3cb3591365cb02fe0fbbcc752e9262718c4a56d`). It identifies QA software 17.0.0, processing time 2026-10-23T14:41:28Z, product version 1.0.11, specification 1.5.0, release P05023, EPSG:32635, track 137, frame 68, and GUNW/L-band/frequency-A metadata. Catalog path and frame cross-checks match. The report is explicitly marked `INCOMPLETE`: `absoluteOrbitNumber` and `listOfObservationModes` are absent, so orbit cross-check is unavailable. The report does not carry a provider QA disposition.

A separate authenticated HDF5 range-read inspected only an allowlist of identification datasets. It retrieved 25,171,789 bytes under a 64 MiB ceiling and read no measurement arrays. Product version, product specification, product type, instrument, mission, frequency, band, look direction, track, and frame were available; `absoluteOrbitNumber` and `listOfObservationModes` were not in the inspected identification group. The PDF and HDF5 results are preserved with source URLs, retrieval metadata, and hashes in [`gunw-p05023-product-metadata-review.json`](../../data/research/gunw-p05023-product-metadata-review.json). A preliminary attempt to read a broader HDF5 metadata group exceeded the same 64 MiB budget; the successful follow-up narrowed the field allowlist instead of raising the limit. No phase, coherence, connected-component, offset, or correction pixels were read.

This evidence supports further evaluation of the P05023 candidate, but does not establish usable displacement data. The provider's `FAIL` remains recorded, expert guidance remains separately attributed, and the incomplete identification report plus unread measurement layers leave scene-specific scientific suitability unresolved.

## ECHO integration assessment

ECHO's application pipeline still reads and analyzes GCOV only. The research probe can retrieve a bounded GUNW QA report and selected identification metadata, but this is not an integrated GUNW analysis path. ECHO has no GUNW phase/geometry interpretation, coherence and connected-component mask policy, phase-to-line-of-sight displacement conversion, or GUNW-specific analysis manifest. GCOV's gamma0 power log-ratio routine is not applicable to GUNW phase values.

GUNW is worth further evaluation under a separate product contract and against product documentation and independent deformation evidence. That work should preserve the interferometric temporal baseline, CRID, polarization, frequency, phase reference, quality masks, ionospheric and external corrections, and the distinction between phase and derived displacement. This screen alone does not justify implementing that adapter.

## Reproduction

With the NISAR optional dependencies installed and Earthdata Login available through the local netrc file, run:

```bash
.venv/bin/python tools/research/screen_gunw_qa.py
```

The discovery script makes bounded metadata searches and QA-summary byte-range reads. The product-review script retrieves one canonical QA PDF and reads only an allowlist of HDF5 identification metadata under a 64 MiB range-read budget; it does not download the multi-gigabyte product or read measurement arrays. Earthdata Login must be available through the local netrc file.

```bash
.venv/bin/python tools/research/inspect_gunw_product_metadata.py \
  --scene-id NISAR_L2_PR_GUNW_032_137_D_068_033_2000_SH_20261009T170432_20261009T170506_20261021T170432_20261021T170507_P05023_N_F_J_001
```

## References

- ASF, [GUNW product definition and data layers](https://nisar-docs.asf.alaska.edu/gunw/).
- NASA, [NISAR subject-matter-expert guidance on PROVISIONAL GUNW identification QA failures](https://forum.earthdata.nasa.gov/viewtopic.php?t=8325).
- ASF, [NISAR product maturities, release dates, and product descriptions](https://nisar-docs.asf.alaska.edu/products-overview/).
- ASF, [NISAR product availability by collection and observation date](https://nisar-docs.asf.alaska.edu/availability-overview/).
- NASA/JPL, [NISAR Level 2 GUNW Product Specification](https://nisar.asf.earthdatacloud.nasa.gov/NISAR-SAMPLE-DATA/DOCS/NISAR_D-102272_RevE_NASA_SDS_Product_Specification_L2_GUNW_Nov8_2024_w-sigs.pdf).
