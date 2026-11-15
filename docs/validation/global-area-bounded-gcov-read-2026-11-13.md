# Bounded NISAR GCOV read after global AOI discovery

**Execution time:** 2026-11-13, approximately 14:23 UTC
**Checkout:** current local `main` source
**Processing path:** `echo.catalog.search_gcov` → `echo.gcov_preview.build_gcov_preview`
**Provider:** ASF NISAR GCOV; Earthdata Login via local `~/.netrc`

## Input and observed result

The live ASF catalog was searched for a small user-selected Dakar-area WGS84 window:

`[-17.4375, 14.7125, -17.4125, 14.7375]` (west, south, east, north)

The search used provisional NISAR L2 GCOV metadata from 2025-07-01 through 2026-11-13 and returned 20 catalog records. ECHO then fetched the provider QA summary and read one bounded remote GCOV window for:

`NISAR_L2_PR_GCOV_033_052_D_081_2005_SHSH_A_20261015T194139_20261015T194213_P05023_N_F_J_001`

The selected measurement layer was `frequency A / HHHH`, in **linear gamma-zero power**. The window contains 18,639 pixel centers inside the requested geographic selection. This is the count of selected grid centers, not a claim that all centers are valid or scientifically usable. The reader returned a single-observation measurement record; ECHO applied no scale or offset to the stored samples. The interface's `10 log10` conversion is a separate visualization transform.

## Provider QA and disposition

ASF's QA summary verdict is **FAIL**. The summary records checks 1, 2, 3, 5, 6, and 7 as `PASS`, while check 4, “Passes all identification group checks?”, is `FAIL`. The product is therefore retained only as a **QA-held diagnostic preview**. No temporal change analysis or physical interpretation is authorized by this read.

QA summary artifact SHA-256: `ce9fd06f3ca9c2007777e3daa66348ebfdf4b3357c6e1b6bb19242e72855303a`
QA artifact retrieval time: `2026-11-13T14:23:08.570963+00:00`
QA artifact range read: 875 bytes in one request. This is the QA-summary transfer size, not the GCOV pixel-window transfer size.

## Verification boundary

This confirms that current-source catalog and preview processing can use a newly submitted, bounded Dakar AOI, retrieve authentic NISAR catalog metadata, obtain the provider QA verdict, and construct a real measurement preview record from a bounded remote product read. It also confirms that the provider QA failure remains visible and restrictive.

This was a direct current-source processing-path check, not a Firefox rendering test of this Dakar raster. It does not validate the measurement values, certify the product, establish a temporal pair, demonstrate calibrated change detection, or support a finding about Dakar. The preview is not saved as a case or investigation record. Its HDF5 window access metrics and array checksums were not retained by this one-off check; a reproducible investigation record would need to preserve the full returned manifest.
