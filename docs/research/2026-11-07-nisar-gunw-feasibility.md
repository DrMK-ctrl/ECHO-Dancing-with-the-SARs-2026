# NISAR GUNW product-path feasibility screen

**Screened:** 2026-11-07 UTC

**Disposition:** Scientifically relevant alternative; one product's metadata and QA report reviewed, provider QA failure retained

**Raster pixels read:** One bounded window for access and encoded-mask characterization; no scientific measurement or event analysis

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

### Tehran same-frame temporal catalog screen

A follow-up ASF query at `POINT(51.4 35.7)` returned 25 PROVISIONAL GUNW catalog products. Nine match descending path 136 / frame 70, all with CRID P05023 and HH catalog polarization, covering these acquisition pairs:

| Reference to secondary acquisition | Provider QA |
|---|---|
| 2026-06-23 to 2026-07-05 | FAIL |
| 2026-07-05 to 2026-07-17 | FAIL |
| 2026-07-17 to 2026-08-10 | FAIL |
| 2026-08-10 to 2026-08-22 | FAIL |
| 2026-08-22 to 2026-09-03 | FAIL |
| 2026-09-03 to 2026-09-15 | FAIL |
| 2026-09-15 to 2026-09-27 | FAIL |
| 2026-09-27 to 2026-10-09 | FAIL |
| 2026-10-09 to 2026-10-21 | FAIL |

Eight products span approximately 12 days. One GUNW pair spans approximately 24 days, from July 17 to August 10. This is an extended interferometric baseline; it is not evidence that an acquisition is missing. The catalog query does not establish whether other acquisitions exist without a matching GUNW product. Each of the nine canonical QA summaries (2,665 bytes, 24 rows) reports 23 PASS checks and the same FAIL, “Passes all `identification` group checks?”. ECHO retains every per-product status; the existing NASA SME guidance about this general PROVISIONAL issue does not replace these records.

The official NISAR known-issues page separately states that the platform collected no data from July 27 to August 10, 2026 and lists this as a permanent gap. That mission-level context overlaps the 24-day July 17–August 10 GUNW pair. It means this pair spans a documented acquisition outage, but cannot identify when within its baseline a surface change occurred. The source relationship and UTC interval calculation are preserved in [`nisar-tehran-frame136-70-mission-gap-context-2026-11-07.json`](../../data/research/nisar-tehran-frame136-70-mission-gap-context-2026-11-07.json). The guide describes platform coverage, not a surface measurement, and does not change the pair's PROVISIONAL maturity or its provider QA `FAIL`. [NASA/ASF NISAR known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/)

The complete catalog features, individual QA CSV checksums, pair baselines, retrieval provenance, and product identifiers are preserved in [`gunw-tehran-frame136-70-temporal-catalog-qa-2026-11-07.json`](../../data/research/gunw-tehran-frame136-70-temporal-catalog-qa-2026-11-07.json). This establishes a promising temporal catalog sequence for further assessment, but not a validated phase series, a deformation trend, or an event finding.

### Bounded pixel characterization of the extended pair

The 2026-07-17 to 2026-08-10 pair was inspected over an approximately 1 km by 1 km WGS84 neighborhood centered on the catalog search point. The 100 m subwindow selected one pixel center; the larger window selected 154 centers. In the larger window, all 154 were finite for phase and coherence, had both reference and secondary subswath support, carried no anomaly flags, had non-water flags, and had connected-component label 1. Coherence ranged from 0.5651 to 0.9560 (mean 0.7967). The uncorrected unwrapped phase ranged from 3.5143 to 3.9864 radians. These are product-layer summaries for this single interferometric pair, not a change estimate or displacement result.

The ionosphere-interpolated mask flag was set at all 154 centers. The corresponding ionosphere phase-screen layer ranges from 18.6745 to 18.7315 radians, and its uncertainty layer from 0.6077 to 0.6319 radians. These ancillary values are recorded as delivered; ECHO did not apply or subtract them. ASF says the GUNW ionosphere screen is not applied to the product phase by default, and this window additionally has the interpolation flag throughout. Product QA remains `FAIL`; the matched `nisarqa` source rule identifies both reference and secondary observation-mode fields as `(NOT SPECIFIED)`, but this cross-check does not replace or explain every provider validation decision. The retained [metadata and QA report review](../../data/research/gunw-tehran-frame136-70-24d-metadata-review-2026-11-07.json), [one-pixel window](../../data/research/gunw-tehran-frame136-70-24d-pixel-window-2026-11-07.json), [154-center four-layer window](../../data/research/gunw-tehran-frame136-70-24d-1km-pixel-window-2026-11-07.json), and [154-center window with ionosphere layers](../../data/research/gunw-tehran-frame136-70-24d-1km-ionosphere-pixel-window-2026-11-07.json) preserve product IDs, source and QA hashes, grid, range-read accounting, processing-tool hashes, and layer hashes.

The larger window required 95,050,411 bytes of authenticated range reads against the 100,663,296-byte limit. Its five scientific arrays are stored in 512 × 512 chunks; the earlier metadata-only probes requested about 66 MB. Thus, the current remote reader can retrieve this small AOI, but its byte-range cost is driven substantially by HDF5 metadata and chunk layout rather than the 154 output samples. The observation is useful for assessing coverage and product limitations, while the persistent QA failure, interpolated ionosphere values, long temporal baseline, and mission outage keep it outside ECHO's cleared measurement path. No phase correction, displacement, change measurement, event extent, or cause inference was performed.

### Product-specific follow-up: Istanbul

NASA's NISAR subject-matter expert replied on October 22, 2026 to a question describing PROVISIONAL GUNW products with an identification-group QA failure and other checks passing. The expert said users may ignore the QA summary “at this stage.” The same reply says consistent CRIDs are suitable for time-series use, mixing P05023 with earlier CRIDs should be done with caution, nominal interferograms are nearest-neighbor acquisitions about 12 days apart, and phase-correction layers are expected to be subtracted from unwrapped phase. It also explains that N/F reflects orbit/attitude accuracy; for nominal products F is usually from attitude, with special care potentially needed for urgent-response products. These are general product-team guidance, not a revised per-scene QA disposition, an explanation of the failed field, or proof that a particular phase measurement is scientifically suitable. ECHO preserves the ASF CSV's `FAIL` alongside the expert guidance rather than replacing either record; the expert reply supports further user evaluation of these products. No correction is applied by ECHO. [NASA Earthdata Forum discussion](https://forum.earthdata.nasa.gov/viewtopic.php?t=8325)

For the Istanbul sample, ECHO retrieved the canonical ASF QA report PDF (1,035,490 bytes; SHA-256 `66578e1e0f86515c2fe4428cd3cb3591365cb02fe0fbbcc752e9262718c4a56d`). It identifies QA software 17.0.0, processing time 2026-10-23T14:41:28Z, product version 1.0.11, specification 1.5.0, release P05023, EPSG:32635, track 137, frame 68, and GUNW/L-band/frequency-A metadata. The version-pinned GUNW 1.5.0 product specification defines `referenceAbsoluteOrbitNumber` and `secondaryAbsoluteOrbitNumber`, plus separate reference and secondary observation-mode fields; it does not use GCOV's `absoluteOrbitNumber` and `listOfObservationModes`. ECHO previously applied the GCOV requirements to this GUNW report and incorrectly called those fields missing. The corrected parser uses product and specification-specific requirements: this report is now `COMPLETE`, and its reference orbit 6291, track 137, and frame 68 match the ASF catalog. The report itself does not carry a provider QA disposition.

A versioned `nisarqa` v17.0.0 source cross-check flags the observed `referenceListOfObservationModes` and `secondaryListOfObservationModes`, both `['(NOT SPECIFIED)']`, as candidate violations of its formatted-mode rule. This is consistent with the aggregate identification failure, but does not prove these are the only failing checks or reproduce the provider's full QA. HDF5 confirms reference/secondary absolute orbits 6291/6464, zero input-data-exception flags, track 137, frame 68, and the two placeholder mode strings.

An authenticated HDF5 metadata inventory then inspected the GUNW phase, coherence, connected-component, mask, coordinate, projection, and selected radar-grid dataset descriptions without reading their raster values. The 4,356 × 4,419 phase, coherence, connected-component, and mask arrays are stored in 512 × 512 chunks; phase units are radians and projection is EPSG:32635. The mask is `uint32`. The pinned GUNW 1.5.0 schema defines its bits as reference-water/subswath encoding, reference and secondary anomaly flags, and an ionospheric interpolation flag; the inspected product's description matches that schema. This resolves the apparent dtype discrepancy with the older Rev E PDF table, which describes the mask as UByte. Selected radar-grid geometry cubes are 20 × 709 × 719, a different grid from the phase arrays; alignment/interpolation must be validated before using them together.

Identification and dataset-inventory metadata used separate HTTPS range-read probes, each capped at 64 MiB. They requested 50,343,529 and 15,732,680 bytes respectively (66,076,209 bytes combined). The PDF, field-level cross-checks, dataset inventory, retrieval metadata, and hashes are preserved in [`gunw-p05023-product-metadata-review.json`](../../data/research/gunw-p05023-product-metadata-review.json). No phase, coherence, connected-component, offset, correction, or geometry-cube pixel values were read.

This evidence supports further evaluation of the P05023 candidate, but does not establish usable displacement data. The provider's `FAIL` remains recorded, expert guidance remains separately attributed, and actual measurement/quality layers have not yet been inspected. The product-specific report parse is complete; that means its documented identification fields were found, not that all science-suitability gates passed.

## Bounded geographic pixel-window characterization

ECHO now has a separate product-specific reader for GUNW v1.5.0 frequency A. It uses authenticated HTTPS byte-range reads against the canonical ASF product URL, requires the phase, coherence, connected-component, and mask arrays together, validates their documented dtypes, units, fill values, shared grid, projection, and pixel-center coordinates, and returns source units without correcting phase or assigning a scientific interpretation. Reads are restricted to at most 262,144 samples, 16 MiB of returned arrays/coordinates, and 96 MiB of remote range traffic. The larger range cap reflects the earlier product metadata probes' 66,076,209-byte total plus the additional compressed chunks needed for a small window; the cap is still enforced per read.

The first reproducible read used the approximate Ayazaga catalog-search point only to verify geographic access; the rectangle is not an event boundary. It selected the 589 pixel centers inside WGS84 bounds `(28.98, 41.095, 29.00, 41.115)` from a 28 × 22 enclosing window on EPSG:32635. The reader requested 81,694,122 bytes and did not request a complete product download. The retained machine-readable record includes the exact window, software-relevant grid metadata, source and QA identifiers, provider QA-artifact hash, per-layer and coordinate hashes, selection details, and summaries for both the enclosing window and selected AOI centers.

The encoded mask's reference and secondary subswath codes are both zero at all 589 selected centers. The pinned GUNW 1.5.0 schema defines zero subswath as no supporting subswath for that input, so this AOI has no supported paired input pixels. All selected `unwrappedPhase` values are finite zeros; coherence is finite (range 0.2467–0.9814), which does not override the mask. These values must not be presented as a zero-displacement measurement.

Two additional bounded windows show spatially different conditions in the same Istanbul scene and in a Tehran-area GUNW scene. A representative interior window in the Istanbul product has a reference-water flag on all 582 selected centers, low coherence (mean 0.0992), and connected-component value zero throughout. This is a water-dominated, low-coherence window, not a deformation sample. The Tehran representative-point window has non-water flag and nonzero reference/secondary subswath codes in all 644 selected centers, no reference or secondary anomaly bits, coherence mean 0.6299 (range 0.1024–0.9207), and component label 1 in 642 centers. However, the ionosphere-interpolated mask bit is set at all 644 centers. The retrieved ionosphere phase-screen values range 35.442–35.614 radians and its uncertainty layer ranges 0.680–0.915 radians; the products' interpolation flag means these ancillary values cannot be silently treated as direct, unmasked estimates or automatically subtracted. The phase values (3.239–5.624 radians) have not been corrected or converted to displacement.

Both scenes' ASF provider QA status remains `FAIL`. NASA's general guidance is retained separately and does not waive these per-product dispositions. The Tehran window is a candidate for further product-specific QA and expert-guided evaluation, not an approved measurement. Across all three windows, no phase correction, phase-to-displacement conversion, change measurement, event extent, or cause inference was performed.

The reader and descriptive record establish authentic, bounded pixel access and expose a concrete suitability limitation. They do not clear the scene for analysis or demonstrate a scientific event finding. The result reinforces the need for the investigation workflow to connect every displayed layer to its temporal pair, encoded quality support, provider disposition, and provenance rather than displaying raw phase alone.

## ECHO integration assessment

ECHO's application pipeline still analyzes GCOV only. The research reader can retrieve bounded GUNW pixels and preserve their access provenance, but it is not yet integrated into application analysis or the interface. ECHO has no validated GUNW phase/geometry interpretation, coherence and connected-component suitability policy, phase-to-line-of-sight displacement conversion, or GUNW analysis manifest. GCOV's gamma0 power log-ratio routine is not applicable to GUNW phase values.

GUNW is worth further evaluation under a separate product contract and against product documentation and independent deformation evidence. That work should preserve the interferometric temporal baseline, CRID, polarization, frequency, phase reference, quality masks, ionospheric and external corrections, and the distinction between phase and derived displacement. This screen alone does not justify implementing that adapter.

## Reproduction

With the NISAR optional dependencies installed and Earthdata Login available through the local netrc file, run:

```bash
.venv/bin/python tools/research/screen_gunw_qa.py
```

The discovery script makes bounded metadata searches and QA-summary byte-range reads. The product-review script retrieves one canonical QA PDF and reads an allowlist of HDF5 identification and dataset-structure metadata in separate probes, each with a 64 MiB range-read budget; it does not download the multi-gigabyte product or read raster values. Earthdata Login must be available through the local netrc file.

To reproduce a same-path/frame temporal catalog and QA screen at another location, provide the point, date range, path, frame, direction, and output path. This captures catalog and provider QA evidence only; it does not read radar pixels or compare phase values:

```bash
.venv/bin/python tools/research/screen_gunw_temporal_series.py \
  --longitude 51.4 --latitude 35.7 \
  --start-date 2026-06-17 --end-date 2026-11-07 \
  --path 136 --frame 70 --direction DESCENDING \
  --maturity PROVISIONAL --max-results 100 \
  --output data/research/gunw-tehran-frame136-70-temporal-catalog-qa-2026-11-07.json
```

```bash
.venv/bin/python tools/research/inspect_gunw_product_metadata.py \
  --scene-id NISAR_L2_PR_GUNW_032_137_D_068_033_2000_SH_20261009T170432_20261009T170506_20261021T170432_20261021T170507_P05023_N_F_J_001
```

The bounded pixel-window characterization is reproduced with:

```bash
.venv/bin/python tools/research/inspect_gunw_window.py
```

This reads one small geographic window from the product, keeps the provider QA `FAIL`, and writes `data/research/gunw-istanbul-ayazaga-pixel-window-2026-11-07.json`. It does not interpret phase or produce a change result. The output's retrieval timestamp is generated at run time; layer hashes and the AOI bounds allow comparison with the retained observation.

To reproduce the Tehran-area read with both ionosphere layers:

```bash
.venv/bin/python tools/research/inspect_gunw_window.py \
  --scene-id NISAR_L2_PR_GUNW_032_136_D_071_033_2000_SH_20261009T152620_20261009T152655_20261021T152620_20261021T152655_P05023_N_F_J_001 \
  --bounds 50.906359 34.663350 50.926359 34.683350 \
  --aoi-label "Tehran product-footprint representative point neighborhood" \
  --include-ionosphere \
  --output data/research/gunw-tehran-footprint-interior-with-ionosphere-pixel-window-2026-11-07.json
```

The inspector records the pinned GUNW schema URL and checksum. This characterization remains separate from the GCOV measurement pipeline.

To inspect the Tehran frame-136/frame-70 24-day pair directly from the retained temporal catalog/QA record, run:

```bash
.venv/bin/python tools/research/inspect_gunw_product_metadata.py \
  --scene-id NISAR_L2_PR_GUNW_025_136_D_070_027_2000_SH_20260717T152548_20260717T152623_20260810T152547_20260810T152622_P05023_N_F_J_001 \
  --screen data/research/gunw-tehran-frame136-70-temporal-catalog-qa-2026-11-07.json \
  --output data/research/gunw-tehran-frame136-70-24d-metadata-review-2026-11-07.json

.venv/bin/python tools/research/inspect_gunw_window.py \
  --scene-id NISAR_L2_PR_GUNW_025_136_D_070_027_2000_SH_20260717T152548_20260717T152623_20260810T152547_20260810T152622_P05023_N_F_J_001 \
  --screen data/research/gunw-tehran-frame136-70-temporal-catalog-qa-2026-11-07.json \
  --bounds 51.395 35.695 51.405 35.705 \
  --aoi-label "approximately 1 km Tehran urban neighborhood centered on the ASF catalog query point" \
  --include-ionosphere \
  --output data/research/gunw-tehran-frame136-70-24d-1km-ionosphere-pixel-window-2026-11-07.json
```

Both commands use Earthdata Login from the local netrc configuration. The pixel reader may take several minutes and enforces its 96 MiB range-read limit; it does not download the full GUNW product or change its QA disposition.

## References

- ASF, [GUNW product definition and data layers](https://nisar-docs.asf.alaska.edu/gunw/).
- NASA, [NISAR subject-matter-expert guidance on PROVISIONAL GUNW identification QA failures](https://forum.earthdata.nasa.gov/viewtopic.php?t=8325).
- ISCE Framework, [`nisarqa` v17.0.0 GUNW product specification 1.5.0](https://github.com/isce-framework/nisarqa/blob/v17.0.0/src/nisarqa/product_specs/1.5.0/nisar_L2_GUNW.xml) (SHA-256 `c75acedfbfe8a5c0893df89336641b690cb296dddce1245f5ae9dafd8891fbd3`).
- ASF, [NISAR product maturities, release dates, and product descriptions](https://nisar-docs.asf.alaska.edu/products-overview/).
- ASF, [NISAR product availability by collection and observation date](https://nisar-docs.asf.alaska.edu/availability-overview/).
- NASA/JPL, [NISAR Level 2 GUNW Product Specification](https://nisar.asf.earthdatacloud.nasa.gov/NISAR-SAMPLE-DATA/DOCS/NISAR_D-102272_RevE_NASA_SDS_Product_Specification_L2_GUNW_Nov8_2024_w-sigs.pdf).
